"""
False Positive Reduction Layer - "Violence or Just Intense?" Classifier

Distinguishes between:
- Sports (boxing, MMA, wrestling, football)
- Action movies / entertainment
- Video games (gameplay, streaming)
- Real violence

This is CRUCIAL for production to avoid false alarms.
"""
import numpy as np
from typing import Dict, Any, Optional, List
from transformers import pipeline
import torch

from ..utils.logging import get_logger

logger = get_logger(__name__)


class FalsePositiveReducer:
    """
    Classifier to distinguish real violence from intense but non-violent content.
    """

    def __init__(self):
        self.classifier = None
        self._model_loaded = False

        # Rule-based indicators for different categories
        self.sports_indicators = {
            'visual': ['stadium', 'arena', 'field', 'court', 'ring', 'scoreboard', 'referee'],
            'audio': ['crowd', 'cheering', 'whistle', 'announcement', 'applause'],
            'text': ['game', 'match', 'score', 'team', 'player', 'sport', 'win', 'goal', 'boxing', 'mma', 'ufc']
        }

        self.entertainment_indicators = {
            'visual': ['cinematic', 'movie', 'film', 'credits', 'subtitle'],
            'audio': ['soundtrack', 'music', 'dramatic'],
            'text': ['trailer', 'scene', 'actor', 'movie', 'film', 'episode', 'show']
        }

        self.gaming_indicators = {
            'visual': ['hud', 'ui', 'healthbar', 'minimap', 'crosshair', 'ammo'],
            'audio': ['voice_chat', 'game_audio'],
            'text': ['game', 'gaming', 'fortnite', 'cod', 'valorant', 'apex', 'pubg', 'warzone', 'gg', 'noob']
        }

    def _load_model(self):
        """Load zero-shot classification model for scene understanding (lazy)."""
        if self._model_loaded:
            return
        try:
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=0 if torch.cuda.is_available() else -1
            )
            if hasattr(self.classifier, 'model'):
                self.classifier.model.eval()
            self._model_loaded = True
            logger.info("False positive reducer loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load false positive reducer: {e}")
            self.classifier = None
            self._model_loaded = True  # Don't retry on failure

    def analyze(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]],
        base_prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze if the violence detected is real or just intense content.

        Args:
            video: Video analysis results
            audio: Audio analysis results
            text: Text analysis results
            base_prediction: Initial violence prediction

        Returns:
            Updated prediction with false positive filtering
        """
        # Only run if violence was detected
        if base_prediction.get('class') != 'Violence':
            return base_prediction

        # Lazy load the model on first use
        self._load_model()

        # Calculate scores for each category
        scores = {
            'sports': self._check_sports_indicators(video, audio, text),
            'entertainment': self._check_entertainment_indicators(video, audio, text),
            'gaming': self._check_gaming_indicators(video, audio, text),
            'real_violence': base_prediction.get('violence_probability', 0.5)
        }

        # Determine category
        category = max(scores.items(), key=lambda x: x[1])
        category_name = category[0]
        category_confidence = category[1]

        logger.info(f"False positive analysis: {category_name} ({category_confidence:.2f})")

        # If non-violence category has high confidence, override or reduce
        if category_name != 'real_violence' and category_confidence > 0.6:
            # Strong indicator of sports/entertainment/gaming
            reduction_factor = min(category_confidence, 0.8)

            updated_confidence = base_prediction['confidence'] * (1 - reduction_factor)

            # Reclassify if confidence drops too low
            if updated_confidence < 40:
                return {
                    **base_prediction,
                    'class': 'Non-Violence',
                    'confidence': 100 - updated_confidence,
                    'original_classification': 'Violence',
                    'false_positive_category': category_name,
                    'false_positive_confidence': float(category_confidence * 100),
                    'reasoning': f"Initially detected as violence, but identified as {category_name} "
                                f"({category_confidence:.0%} confidence) | " + base_prediction.get('reasoning', '')
                }
            else:
                return {
                    **base_prediction,
                    'confidence': float(updated_confidence),
                    'false_positive_warning': category_name,
                    'false_positive_confidence': float(category_confidence * 100),
                    'reasoning': f"Warning: Possible {category_name} content "
                                f"({category_confidence:.0%}) | " + base_prediction.get('reasoning', '')
                }

        # Real violence - no changes
        return {
            **base_prediction,
            'false_positive_check': 'passed',
            'category_scores': {k: float(v) for k, v in scores.items()}
        }

    def _check_sports_indicators(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> float:
        """Check for sports indicators."""
        score = 0.0
        count = 0

        # Check text indicators
        if text:
            text_content = str(text).lower()
            matches = sum(1 for indicator in self.sports_indicators['text'] if indicator in text_content)
            if matches > 0:
                score += min(matches * 0.15, 0.6)
                count += 1

        # Check audio indicators (crowd sounds, cheering)
        if audio and 'detected_sounds' in audio:
            sounds = str(audio['detected_sounds']).lower()
            matches = sum(1 for indicator in self.sports_indicators['audio'] if indicator in sounds)
            if matches > 0:
                score += min(matches * 0.2, 0.4)
                count += 1

        # Check for organized/structured violence (boxing, MMA patterns)
        if video:
            # Temporal consistency in sports is different (alternating action)
            temporal = video.get('temporal_consistency', 0)
            if 0.3 < temporal < 0.6:  # Moderate consistency (not sustained like real violence)
                score += 0.3
                count += 1

        return score / max(count, 1) if count > 0 else 0.0

    def _check_entertainment_indicators(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> float:
        """Check for movie/TV show indicators."""
        score = 0.0
        count = 0

        # Check text
        if text:
            text_content = str(text).lower()
            matches = sum(1 for indicator in self.entertainment_indicators['text'] if indicator in text_content)
            if matches > 0:
                score += min(matches * 0.2, 0.7)
                count += 1

        # Check for cinematic qualities (high production value)
        if video:
            # Movies tend to have high visual quality and dramatic composition
            # This is a placeholder - in production you'd check resolution, composition, etc.
            pass

        # Check audio for soundtrack/dramatic music
        if audio and 'detected_sounds' in audio:
            sounds = str(audio['detected_sounds']).lower()
            if any(indicator in sounds for indicator in self.entertainment_indicators['audio']):
                score += 0.4
                count += 1

        return score / max(count, 1) if count > 0 else 0.0

    def _check_gaming_indicators(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> float:
        """Check for video game indicators."""
        score = 0.0
        count = 0

        # Check text (strongest indicator for gaming)
        if text:
            text_content = str(text).lower()
            # Check for gaming context
            gaming_context = text.get('context', {})
            if gaming_context.get('is_gaming'):
                score += 0.8
                count += 1
            else:
                matches = sum(1 for indicator in self.gaming_indicators['text'] if indicator in text_content)
                if matches > 0:
                    score += min(matches * 0.2, 0.6)
                    count += 1

        # Video games have distinctive visual patterns
        if video:
            # Check for UI elements, HUD, etc. (would need object detection)
            # Placeholder for production implementation
            pass

        return score / max(count, 1) if count > 0 else 0.0


# Global instance
_reducer = None


def get_false_positive_reducer() -> FalsePositiveReducer:
    """Get or create global false positive reducer instance."""
    global _reducer
    if _reducer is None:
        _reducer = FalsePositiveReducer()
    return _reducer
