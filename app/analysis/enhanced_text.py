"""
Enhanced Text Analyzer with multi-model ensemble.
ToxicBERT + RoBERTa-offensive + keyword detection.
"""
from typing import Dict, Any, List

import torch

from .base import BaseAnalyzer
from .text_analyzer import TextAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class EnhancedTextAnalyzer(BaseAnalyzer):
    """Multi-model ensemble text analyzer."""

    def __init__(self):
        super().__init__()
        self._modality = 'text'
        self.config = get_config().text
        self.model_manager = get_model_manager()
        self.base_analyzer = TextAnalyzer()

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text with ensemble: ToxicBERT + RoBERTa-offensive + keywords."""
        # Get base result (keyword + ToxicBERT)
        base_result = self.base_analyzer.analyze(text)

        # Get offensive model result
        offensive_result = self._analyze_offensive(text)

        # Extract individual scores
        keyword_score = 0
        for kw in base_result.get('keywords_found', []):
            keyword_score += 15  # approximate per-keyword
        keyword_score = min(100, keyword_score)

        toxic_score = base_result.get('ml_score', 0)
        offensive_score = offensive_result.get('score', 0)

        # Weighted ensemble: 0.4*toxic + 0.3*offensive + 0.3*keyword
        ensemble_score = 0.4 * toxic_score + 0.3 * offensive_score + 0.3 * keyword_score

        is_violent = (
            base_result.get('class') == 'Violence' or
            offensive_score > 70 or
            ensemble_score > 50
        )

        reasoning_parts = []
        if base_result.get('keywords_found'):
            reasoning_parts.append(f"Keywords: {', '.join(base_result['keywords_found'][:3])}")
        if toxic_score > 50:
            reasoning_parts.append(f"ToxicBERT: {toxic_score:.0f}%")
        if offensive_score > 50:
            reasoning_parts.append(f"Offensive model: {offensive_score:.0f}%")

        confidence = min(95, max(60, ensemble_score + 20)) if is_violent else max(60, 100 - ensemble_score)

        result = self._create_result(
            is_violent=is_violent,
            confidence=confidence,
            reasoning=' | '.join(reasoning_parts) if reasoning_parts else base_result.get('reasoning', ''),
            keywords_found=base_result.get('keywords_found', []),
            ml_score=toxic_score,
            offensive_score=offensive_score,
            ensemble_score=float(ensemble_score),
            ensemble_method='toxic_offensive_keyword',
        )

        # Carry over violations
        result['violations'] = base_result.get('violations', [])
        return result

    def _analyze_offensive(self, text: str) -> Dict[str, Any]:
        """Analyze text with RoBERTa offensive model."""
        try:
            classifier = self.model_manager.offensive_classifier
            if classifier is None:
                return {'label': 'not-offensive', 'score': 0}

            with torch.no_grad():
                result = classifier(text[:512])[0]

            label = result['label'].lower()
            score = result['score'] * 100

            # RoBERTa-offensive outputs 'offensive' or 'not-offensive'
            if 'offensive' in label and 'not' not in label:
                return {'label': label, 'score': score}
            else:
                return {'label': label, 'score': 100 - score}

        except Exception as e:
            logger.warning(f"Offensive model analysis failed: {e}")
            return {'label': 'error', 'score': 0, 'error': str(e)}
