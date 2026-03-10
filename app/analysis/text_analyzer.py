"""
Text content analyzer for Violence Detection System.
Analyzes text for violence/toxicity with keyword detection and ML classification.
"""
import re
from typing import Dict, Any, List, Optional

import torch

from .base import BaseAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.errors import AnalysisError


class TextAnalyzer(BaseAnalyzer):
    """Analyzes text content for violence indicators."""

    # Violence keywords organized by category
    VIOLENCE_KEYWORDS = {
        'extreme': ['kill', 'murder', 'assassinate', 'slaughter', 'massacre', 'execute'],
        'physical': ['beat', 'punch', 'kick', 'stab', 'shoot', 'hit', 'attack', 'assault', 'fight'],
        'weapons': ['gun', 'knife', 'weapon', 'bomb', 'explosive', 'rifle', 'pistol'],
        'threats': ['threat', 'threaten', 'hurt', 'harm', 'injure', 'damage', 'destroy'],
        'hate': ['hate', 'despise', 'loathe', 'detest'],
        'death': ['death', 'die', 'dead', 'corpse', 'blood', 'bleed'],
        'abuse': ['abuse', 'torture', 'rape', 'kidnap', 'hostage']
    }

    # Threatening patterns
    THREAT_PATTERNS = [
        r'i (will|gonna|going to) (kill|hurt|beat|destroy)',
        r'you (will|gonna|going to) (die|suffer|regret)',
        r'(deserve|should|must) (die|death|suffer)',
    ]

    def __init__(self):
        super().__init__()
        self._modality = 'text'
        self.config = get_config().text
        self.model_manager = get_model_manager()

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze text content for violence detection.

        Args:
            text: Text content to analyze

        Returns:
            Analysis result dictionary
        """
        if not text or len(text.strip()) == 0:
            return self._create_error_result("No text content provided")

        # Use enhanced analyzer when enabled
        config = get_config()
        if config.model.use_enhanced_models:
            try:
                from .enhanced_text import EnhancedTextAnalyzer
                enhanced = EnhancedTextAnalyzer()
                return enhanced.analyze(text)
            except Exception as e:
                self.logger.warning(f"Enhanced text failed, falling back: {e}")

        return self._analyze_base(text)

    def _analyze_base(self, text: str) -> Dict[str, Any]:
        """Base text analysis (original implementation)."""
        try:
            text_lower = text.lower()

            # Keyword analysis
            found_keywords, keyword_score = self._analyze_keywords(text_lower)

            # Pattern analysis
            pattern_matches = self._analyze_patterns(text_lower)
            if pattern_matches:
                keyword_score += self.config.threat_pattern_score * len(pattern_matches)
                found_keywords.extend([f"direct threat ({p})" for p in pattern_matches])

            # ML analysis
            ml_result = self._analyze_with_ml(text)
            ml_detected_violence = self._is_ml_violence(ml_result)

            # Combine scores
            combined_score = self._calculate_combined_score(
                keyword_score, found_keywords, ml_result, ml_detected_violence
            )

            # Determine if violent
            is_violent = self._is_violent(keyword_score, ml_detected_violence, found_keywords)

            # Build result
            return self._build_result(
                is_violent, combined_score, found_keywords, ml_result, ml_detected_violence
            )

        except Exception as e:
            self.logger.error(f"Text analysis failed: {e}")
            raise AnalysisError(
                f"Text analysis failed",
                analysis_type='text',
                details={'error': str(e)}
            )

    def analyze_temporal(self, text: str) -> Dict[str, Any]:
        """
        Analyze text with per-sentence violation detection.
        Returns standard result plus violations list.
        """
        from .temporal import TextTemporalDetector

        result = self.analyze(text)

        try:
            detector = TextTemporalDetector()
            classifier = self.model_manager.text_classifier
            result['violations'] = detector.detect(
                text, classifier, self.VIOLENCE_KEYWORDS, self.config
            )
        except Exception as e:
            self.logger.error(f"Temporal text analysis failed: {e}")
            result['violations'] = []

        return result

    def _analyze_keywords(self, text_lower: str) -> tuple[List[str], int]:
        """Analyze text for violence keywords."""
        found_keywords = []
        violence_score = 0

        for category, words in self.VIOLENCE_KEYWORDS.items():
            for word in words:
                if word in text_lower:
                    found_keywords.append(f"{word} ({category})")

                    if category == 'extreme':
                        violence_score += self.config.extreme_keyword_score
                    elif category == 'physical':
                        violence_score += self.config.physical_keyword_score
                    elif category in ['weapons', 'threats']:
                        violence_score += self.config.weapons_threats_score
                    else:
                        violence_score += self.config.other_keyword_score

        return found_keywords, violence_score

    def _analyze_patterns(self, text_lower: str) -> List[str]:
        """Analyze text for threatening patterns."""
        matches = []
        for pattern in self.THREAT_PATTERNS:
            if re.search(pattern, text_lower):
                matches.append(pattern)
        return matches

    def _analyze_with_ml(self, text: str) -> Dict[str, Any]:
        """Analyze text using ML model."""
        classifier = self.model_manager.text_classifier
        with torch.no_grad():
            result = classifier(text[:512])[0]
        return {
            'label': result['label'].lower(),
            'score': max(0, min(100, result['score'] * 100))
        }

    def _is_ml_violence(self, ml_result: Dict[str, Any]) -> bool:
        """Check if ML model detected violence."""
        return (
            (ml_result['label'] == 'toxic' and ml_result['score'] > self.config.ml_toxic_threshold) or
            (ml_result['label'] == 'negative' and ml_result['score'] > self.config.ml_negative_threshold)
        )

    def _calculate_combined_score(
        self,
        keyword_score: int,
        found_keywords: List[str],
        ml_result: Dict[str, Any],
        ml_detected_violence: bool
    ) -> float:
        """Calculate combined violence score."""
        if found_keywords:
            return min(keyword_score, 100)
        elif ml_detected_violence:
            return ml_result['score']
        return 0

    def _is_violent(
        self,
        keyword_score: int,
        ml_detected_violence: bool,
        found_keywords: List[str]
    ) -> bool:
        """Determine if text is violent based on analysis."""
        return (
            keyword_score > self.config.keyword_threshold or
            ml_detected_violence or
            len(found_keywords) > 0
        )

    def _build_result(
        self,
        is_violent: bool,
        combined_score: float,
        found_keywords: List[str],
        ml_result: Dict[str, Any],
        ml_detected_violence: bool
    ) -> Dict[str, Any]:
        """Build the final result dictionary."""
        reasoning = []
        if found_keywords:
            reasoning.append(f"Found {len(found_keywords)} violence indicators: {', '.join(found_keywords[:5])}")
        if ml_detected_violence:
            reasoning.append(f"ML model detected: {ml_result['label']} ({ml_result['score']:.1f}% confidence)")

        if is_violent:
            final_confidence = max(combined_score + self.config.confidence_boost, self.config.min_confidence)
            return self._create_result(
                is_violent=True,
                confidence=max(0, min(100, min(final_confidence, self.config.max_confidence))),
                reasoning=' | '.join(reasoning) if reasoning else 'Toxic content detected',
                keywords_found=found_keywords[:10],
                ml_score=ml_result['score']
            )
        else:
            return self._create_result(
                is_violent=False,
                confidence=max(100 - combined_score, self.config.min_confidence),
                reasoning='No significant violence indicators found',
                keywords_found=[],
                ml_score=ml_result['score']
            )
