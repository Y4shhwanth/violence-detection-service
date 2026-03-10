"""
Context detector for violence detection.
Extracts benign context detection from fusion.py + adds zero-shot classification.
"""
from typing import Dict, Any, List, Optional

from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)

CONTEXT_CATEGORIES = {
    'sports': {
        'keywords': {
            'boxing', 'boxer', 'fight card', 'mma', 'ufc', 'wrestling', 'wrestler',
            'match', 'tournament', 'championship', 'referee', 'round', 'knockout',
            'ring', 'arena', 'stadium', 'athlete', 'player', 'team', 'coach',
            'football', 'soccer', 'hockey', 'rugby', 'martial arts', 'karate',
            'taekwondo', 'judo', 'sparring', 'bout', 'heavyweight', 'lightweight',
            'sport', 'competition', 'league', 'score', 'goal',
        },
        'reduction': 0.25,
        'zero_shot_label': 'This is about a sports event or athletic competition',
    },
    'gaming': {
        'keywords': {
            'game', 'gaming', 'gamer', 'video game', 'gameplay', 'esports',
            'console', 'controller', 'level', 'boss fight', 'respawn', 'fps',
            'multiplayer', 'fortnite', 'call of duty', 'minecraft',
            'playstation', 'xbox', 'nintendo', 'steam', 'twitch',
        },
        'reduction': 0.20,
        'zero_shot_label': 'This is about video games or gaming',
    },
    'movie': {
        'keywords': {
            'movie', 'film', 'scene', 'actor', 'actress', 'director',
            'screenplay', 'cinema', 'trailer', 'sequel', 'prequel',
            'fictional', 'character', 'plot', 'storyline', 'episode',
            'series', 'tv show', 'netflix', 'hbo', 'disney',
        },
        'reduction': 0.20,
        'zero_shot_label': 'This is about a movie, TV show, or fictional content',
    },
    'news': {
        'keywords': {
            'reported', 'according to', 'news', 'journalist', 'reporter',
            'investigation', 'incident report', 'press conference', 'officials said',
            'authorities', 'police report', 'statement released',
        },
        'reduction': 0.15,
        'zero_shot_label': 'This is a news report or journalistic content',
    },
}


class ContextDetector:
    """Detects benign context (sports, gaming, movies, news) in content."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.config = get_config()
        self._initialized = True

    def detect(self, predictions: List[Dict[str, Any]], text: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect context from predictions and optional text.
        Returns: {context_type, reduction_factor, confidence, method}
        """
        # Collect all text from predictions
        all_text = self._extract_text(predictions)
        if text:
            all_text += ' ' + text.lower()

        if not all_text.strip():
            return {'context_type': None, 'reduction_factor': 0.0, 'confidence': 0, 'method': 'none'}

        # Keyword-based detection
        keyword_result = self._detect_keywords(all_text)

        # Zero-shot classification (if enhanced models enabled)
        use_enhanced = self.config.model.use_enhanced_models
        if use_enhanced and keyword_result['confidence'] < 80:
            zs_result = self._detect_zero_shot(all_text[:512])
            if zs_result and zs_result['confidence'] > keyword_result['confidence']:
                return zs_result

        return keyword_result

    def _extract_text(self, predictions: List[Dict[str, Any]]) -> str:
        """Extract all text from predictions for context analysis."""
        parts = []
        for pred in predictions:
            reasoning = pred.get('reasoning', '')
            if isinstance(reasoning, str):
                parts.append(reasoning.lower())
            for kw in pred.get('keywords_found', []):
                parts.append(kw.lower())
            if pred.get('modality') == 'text':
                for v in pred.get('violations', []):
                    sentence = v.get('sentence', '')
                    if sentence:
                        parts.append(sentence.lower())
        return ' '.join(parts)

    def _detect_keywords(self, text: str) -> Dict[str, Any]:
        """Keyword-based context detection."""
        best_context = None
        best_hits = 0
        best_reduction = 0.0

        for ctx_type, ctx_info in CONTEXT_CATEGORIES.items():
            hits = sum(1 for kw in ctx_info['keywords'] if kw in text)
            if hits > best_hits:
                best_hits = hits
                best_context = ctx_type
                best_reduction = ctx_info['reduction']

        if best_hits >= 3:
            return {
                'context_type': best_context,
                'reduction_factor': best_reduction,
                'confidence': min(95, best_hits * 15),
                'method': 'keyword',
                'keyword_hits': best_hits,
            }
        elif best_hits >= 2:
            return {
                'context_type': best_context,
                'reduction_factor': best_reduction * 0.6,
                'confidence': best_hits * 15,
                'method': 'keyword',
                'keyword_hits': best_hits,
            }

        return {'context_type': None, 'reduction_factor': 0.0, 'confidence': 0, 'method': 'keyword'}

    def _detect_zero_shot(self, text: str) -> Optional[Dict[str, Any]]:
        """Zero-shot classification for context detection."""
        try:
            manager = get_model_manager()
            classifier = manager.zero_shot_classifier
            if classifier is None:
                return None

            import torch

            candidate_labels = [info['zero_shot_label'] for info in CONTEXT_CATEGORIES.values()]
            ctx_types = list(CONTEXT_CATEGORIES.keys())

            with torch.no_grad():
                result = classifier(text, candidate_labels, multi_label=False)

            top_label = result['labels'][0]
            top_score = result['scores'][0] * 100

            # Find matching context type
            idx = candidate_labels.index(top_label)
            ctx_type = ctx_types[idx]

            if top_score > 60:
                return {
                    'context_type': ctx_type,
                    'reduction_factor': CONTEXT_CATEGORIES[ctx_type]['reduction'],
                    'confidence': top_score,
                    'method': 'zero_shot',
                }

            return None

        except Exception as e:
            logger.warning(f"Zero-shot context detection failed: {e}")
            return None


_context_detector = None


def get_context_detector() -> ContextDetector:
    global _context_detector
    if _context_detector is None:
        _context_detector = ContextDetector()
    return _context_detector
