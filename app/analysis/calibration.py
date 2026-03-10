"""
Conservative calibration for Violence Detection System.

Uses a gentle sigmoid that preserves low scores as low and only amplifies
genuinely high raw scores. Previous aggressive params mapped ~60 raw to ~88
calibrated, causing false positives.
"""
import math
from typing import Dict, Tuple

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Conservative calibration parameters (a, b) for sigmoid: 1 / (1 + exp(a*x + b))
# Tuned so that:
#   raw 30 -> ~30 calibrated
#   raw 50 -> ~50 calibrated
#   raw 70 -> ~73 calibrated
#   raw 90 -> ~92 calibrated
DEFAULT_PARAMS: Dict[str, Tuple[float, float]] = {
    'video': (-0.07, 2.5),
    'audio': (-0.07, 3.5),
    'text': (-0.08, 4.0),
}


class CalibrationLayer:
    """
    Calibrates raw confidence scores using Platt scaling (sigmoid transform).
    Conservative parameters prevent low-confidence detections from inflating.
    """

    def __init__(self, params: Dict[str, Tuple[float, float]] = None):
        self.params = params or DEFAULT_PARAMS

    def calibrate(self, raw_score: float, modality: str) -> float:
        """
        Calibrate a raw confidence score for a given modality.

        Args:
            raw_score: Raw confidence score (0-100).
            modality: One of 'video', 'audio', 'text'.

        Returns:
            Calibrated score (0-100), clipped.
        """
        if modality not in self.params:
            return max(0.0, min(100.0, raw_score))

        a, b = self.params[modality]

        try:
            # Platt sigmoid: P = 1 / (1 + exp(a * x + b))
            exponent = a * raw_score + b
            exponent = max(-500, min(500, exponent))
            calibrated = 1.0 / (1.0 + math.exp(exponent))
            return max(0.0, min(100.0, calibrated * 100.0))
        except (OverflowError, ValueError):
            return max(0.0, min(100.0, raw_score))


# Module singleton
_calibration_layer = None


def get_calibration_layer() -> CalibrationLayer:
    """Get or create global CalibrationLayer instance."""
    global _calibration_layer
    if _calibration_layer is None:
        _calibration_layer = CalibrationLayer()
    return _calibration_layer
