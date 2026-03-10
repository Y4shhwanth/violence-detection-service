"""
Violence Risk Scoring System.

Computes a unified risk score (0-100) from multi-modal analysis results
using weighted combination: 0.5 * video + 0.3 * audio + 0.2 * text.

Severity levels:
    - Low       (0-40):   Content appears safe
    - Moderate  (40-70):  Some indicators present, review recommended
    - High      (70-90):  Strong indicators, likely violation
    - Critical  (90-100): Severe violence detected, immediate action needed
"""
from typing import Dict, Any, Optional, List

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Modality weights for risk calculation
MODALITY_WEIGHTS = {
    'video': 0.5,
    'audio': 0.3,
    'text': 0.2,
}

# Severity level thresholds and metadata
SEVERITY_LEVELS = [
    {'min': 90, 'max': 100, 'level': 'Critical', 'color': '#dc2626',
     'recommendation': 'Immediate removal recommended. Content contains severe violent indicators.'},
    {'min': 70, 'max': 89,  'level': 'High', 'color': '#f97316',
     'recommendation': 'Content flagged for urgent review. Strong violence indicators detected.'},
    {'min': 40, 'max': 69,  'level': 'Moderate', 'color': '#eab308',
     'recommendation': 'Manual review recommended before publishing. Some indicators present.'},
    {'min': 0,  'max': 39,  'level': 'Low', 'color': '#22c55e',
     'recommendation': 'Content appears safe. No significant violence indicators found.'},
]


class RiskScorer:
    """
    Computes a weighted risk score from multi-modal analysis predictions.

    The scorer extracts violence probability from each modality, applies
    configurable weights, and maps the result to a severity level with
    a human-readable recommendation.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.weights = MODALITY_WEIGHTS.copy()
        self.severity_levels = SEVERITY_LEVELS

    def compute_risk(
        self,
        video_prediction: Optional[Dict[str, Any]] = None,
        audio_prediction: Optional[Dict[str, Any]] = None,
        text_prediction: Optional[Dict[str, Any]] = None,
        fused_prediction: Optional[Dict[str, Any]] = None,
        violations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Compute the overall violence risk score from modality predictions.

        Args:
            video_prediction: Video analyzer output (class, confidence).
            audio_prediction: Audio analyzer output (class, confidence).
            text_prediction:  Text analyzer output (class, confidence).
            fused_prediction: Fused prediction (used for calibrated scores).
            violations:       List of detected violation events.

        Returns:
            Dict with violence_probability, severity, risk_level,
            recommendation, per-modality scores, and contributing factors.
        """
        # Extract per-modality violence probability (0-100)
        video_score = self._extract_violence_score(video_prediction, 'video')
        audio_score = self._extract_violence_score(audio_prediction, 'audio')
        text_score = self._extract_violence_score(text_prediction, 'text')

        scores = {
            'video': video_score,
            'audio': audio_score,
            'text': text_score,
        }

        # Use calibrated scores from fusion if available (more accurate),
        # but only for modalities that classified as Violence. For Non-Violence
        # modalities, high calibrated = high confidence it's safe, so invert.
        if fused_prediction:
            calibrated = fused_prediction.get('calibrated_scores', {})
            if calibrated:
                predictions_map = {}
                for pred in [video_prediction, audio_prediction, text_prediction]:
                    if pred and pred.get('modality'):
                        predictions_map[pred['modality']] = pred
                for modality in scores:
                    if modality in calibrated:
                        cal_score = float(calibrated[modality])
                        pred = predictions_map.get(modality)
                        if pred and pred.get('class') == 'Violence':
                            scores[modality] = cal_score
                        else:
                            # Non-Violence: invert calibrated score
                            scores[modality] = max(0.0, 100.0 - cal_score)

        # Weighted combination
        weighted_sum = 0.0
        total_weight = 0.0
        active_modalities = []

        for modality, score in scores.items():
            if score > 0:
                w = self.weights.get(modality, 0.2)
                weighted_sum += w * score
                total_weight += w
                active_modalities.append(modality)

        # Normalize by active weights (redistribute if a modality is missing)
        if total_weight > 0:
            violence_probability = weighted_sum / total_weight
        else:
            violence_probability = 0.0

        # Clamp to 0-100
        violence_probability = max(0.0, min(100.0, violence_probability))

        # Apply violation count boost (more violations = higher risk)
        violation_boost = self._compute_violation_boost(violations)
        violence_probability = min(100.0, violence_probability + violation_boost)

        # Map to severity level
        severity_info = self._get_severity(violence_probability)

        # Identify contributing factors
        factors = self._identify_factors(
            scores, video_prediction, audio_prediction, text_prediction, violations
        )

        result = {
            'violence_probability': round(violence_probability, 1),
            'severity': severity_info['level'],
            'risk_level': severity_info['level'],
            'risk_color': severity_info['color'],
            'recommendation': severity_info['recommendation'],
            'modality_scores': {k: round(v, 1) for k, v in scores.items()},
            'active_modalities': active_modalities,
            'contributing_factors': factors,
            'violation_count': len(violations) if violations else 0,
            'violation_boost': round(violation_boost, 1),
        }

        logger.info(
            f"Risk score: {violence_probability:.1f} ({severity_info['level']}), "
            f"modalities={active_modalities}, factors={len(factors)}"
        )

        return result

    def _extract_violence_score(
        self, prediction: Optional[Dict[str, Any]], modality: str
    ) -> float:
        """
        Extract a violence probability (0-100) from a modality prediction.

        If the modality classified as 'Violence', use its confidence directly.
        If 'Non-Violence', invert the confidence to get violence probability.
        """
        if not prediction or prediction.get('class') == 'Error':
            return 0.0

        confidence = float(prediction.get('confidence', 0))
        classification = prediction.get('class', 'Non-Violence')

        if classification == 'Violence':
            return confidence
        else:
            # Invert: high non-violence confidence = low violence probability
            return max(0.0, 100.0 - confidence)

    def _compute_violation_boost(
        self, violations: Optional[List[Dict[str, Any]]]
    ) -> float:
        """
        Compute a small boost based on the number and severity of violations.
        Capped at +10 to avoid over-inflation.
        """
        if not violations:
            return 0.0

        count = len(violations)
        # Each violation adds +2, capped at +10
        base_boost = min(10.0, count * 2.0)

        # Extra boost for high-confidence violations
        high_conf_violations = sum(
            1 for v in violations
            if v.get('confidence', 0) > 80
        )
        extra = min(5.0, high_conf_violations * 1.5)

        return min(10.0, base_boost + extra)

    def _get_severity(self, score: float) -> Dict[str, str]:
        """Map a 0-100 score to a severity level with color and recommendation."""
        for level in self.severity_levels:
            if score >= level['min']:
                return level
        # Fallback
        return self.severity_levels[-1]

    def _identify_factors(
        self,
        scores: Dict[str, float],
        video_pred: Optional[Dict],
        audio_pred: Optional[Dict],
        text_pred: Optional[Dict],
        violations: Optional[List[Dict]],
    ) -> List[Dict[str, Any]]:
        """
        Identify the top contributing factors to the risk score.
        Returns a list of factor dicts with source, description, and impact.
        """
        factors = []

        # Video factors
        if video_pred and scores.get('video', 0) > 30:
            violent_frames = video_pred.get('violent_frames', [])
            if violent_frames:
                factors.append({
                    'source': 'video',
                    'description': f'{len(violent_frames)} violent frame(s) detected',
                    'impact': 'high' if scores['video'] > 70 else 'medium',
                })
            ml_class = video_pred.get('ml_classification', '')
            if ml_class and 'violence' in str(ml_class).lower():
                factors.append({
                    'source': 'video',
                    'description': f'ML classification: {ml_class}',
                    'impact': 'high',
                })

        # Audio factors
        if audio_pred and scores.get('audio', 0) > 30:
            detected_sounds = audio_pred.get('detected_sounds', [])
            if detected_sounds:
                top_sounds = detected_sounds[:3]
                factors.append({
                    'source': 'audio',
                    'description': f'Detected sounds: {", ".join(top_sounds)}',
                    'impact': 'high' if scores['audio'] > 70 else 'medium',
                })

        # Text factors
        if text_pred and scores.get('text', 0) > 30:
            keywords = text_pred.get('keywords_found', [])
            if keywords:
                top_kw = keywords[:5]
                factors.append({
                    'source': 'text',
                    'description': f'Keywords: {", ".join(top_kw)}',
                    'impact': 'high' if scores['text'] > 70 else 'medium',
                })
            ml_score = text_pred.get('ml_score', 0)
            if ml_score > 50:
                factors.append({
                    'source': 'text',
                    'description': f'Toxicity ML score: {ml_score:.0f}%',
                    'impact': 'high' if ml_score > 80 else 'medium',
                })

        # Violation event factors
        if violations:
            modalities_with_violations = set(v.get('modality', '') for v in violations)
            if len(modalities_with_violations) > 1:
                factors.append({
                    'source': 'cross_modal',
                    'description': f'Violations in {len(modalities_with_violations)} modalities',
                    'impact': 'high',
                })

        return factors


# Singleton accessor
_risk_scorer = None


def get_risk_scorer() -> RiskScorer:
    """Get or create the global RiskScorer instance."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer
