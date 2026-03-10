"""
Severity scoring module for Violence Detection System.

Computes a 0-100 severity score from analyzer outputs using a deterministic,
rule-based formula. No training required.
"""
from typing import Dict, Any, List, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Keywords that indicate weapon involvement
WEAPON_KEYWORDS = frozenset({
    'gun', 'knife', 'weapon', 'bomb', 'explosive', 'rifle', 'pistol',
    'sword', 'machete', 'grenade', 'firearm',
})

# Severity label thresholds
SEVERITY_LABELS = [
    (80, 'Critical'),
    (60, 'Severe'),
    (40, 'Moderate'),
    (0, 'Mild'),
]


def compute_severity(
    video_result: Optional[Dict[str, Any]],
    audio_result: Optional[Dict[str, Any]],
    text_result: Optional[Dict[str, Any]],
    fused_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute a severity score (0-100) from modality results.

    Formula (no training):
        base  = average of valid modality confidences (scaled 0-100)
        +20   if exactly 2 modalities detect violence
        +35   if all 3 modalities detect violence
        +15   if weapon-related keywords detected in any modality
        cap   at 100

    Args:
        video_result: Video analyzer output (or None)
        audio_result: Audio analyzer output (or None)
        text_result:  Text analyzer output (or None)
        fused_result: Fused prediction (optional, used for metadata)

    Returns:
        {
            "severity_score": int,
            "severity_label": "Mild" | "Moderate" | "Severe" | "Critical",
            "breakdown": {
                "base_confidence": float,
                "multi_modal_bonus": int,
                "weapon_bonus": int,
                "modalities_violent": int,
                "total_modalities": int,
            }
        }
    """
    modality_results = [
        ('video', video_result),
        ('audio', audio_result),
        ('text', text_result),
    ]

    # Collect confidences and violence flags from valid results
    confidences: List[float] = []
    violence_count = 0
    total_modalities = 0

    for name, result in modality_results:
        if result is None or result.get('class') == 'Error':
            continue
        total_modalities += 1
        confidences.append(float(result.get('confidence', 0)))
        if result.get('class') == 'Violence':
            violence_count += 1

    # Base: average confidence across valid modalities
    if confidences:
        base_confidence = sum(confidences) / len(confidences)
    else:
        base_confidence = 0.0

    # Conservative multi-modal agreement bonus (reduced from +20/+35)
    multi_modal_bonus = 0
    if violence_count >= 3:
        multi_modal_bonus = 10
    elif violence_count == 2:
        multi_modal_bonus = 5

    # Weapon keyword bonus (reduced from +15)
    weapon_bonus = 0
    if _has_weapon_keywords(video_result, audio_result, text_result):
        weapon_bonus = 8

    # Final score, capped at 100
    raw_score = base_confidence + multi_modal_bonus + weapon_bonus
    severity_score = int(min(raw_score, 100))

    # No severity if violence was not detected by any modality
    if violence_count == 0:
        severity_score = 0

    severity_label = _score_to_label(severity_score)

    logger.info(
        f"Severity computed: score={severity_score}, label={severity_label}, "
        f"violent_modalities={violence_count}/{total_modalities}"
    )

    return {
        'severity_score': severity_score,
        'severity_label': severity_label,
        'breakdown': {
            'base_confidence': round(base_confidence, 2),
            'multi_modal_bonus': multi_modal_bonus,
            'weapon_bonus': weapon_bonus,
            'modalities_violent': violence_count,
            'total_modalities': total_modalities,
        }
    }


def _has_weapon_keywords(
    video_result: Optional[Dict[str, Any]],
    audio_result: Optional[Dict[str, Any]],
    text_result: Optional[Dict[str, Any]],
) -> bool:
    """Check if any modality detected weapon-related content."""
    # Check text keywords
    if text_result:
        keywords = text_result.get('keywords_found', [])
        for kw in keywords:
            # keywords are formatted as "word (category)"
            word = kw.split('(')[0].strip().lower()
            if word in WEAPON_KEYWORDS:
                return True

    # Check video frame indicators
    if video_result:
        for frame in video_result.get('violent_frames', []):
            indicators = frame.get('indicators', [])
            ml_detection = frame.get('ml_detection', '')
            combined = ' '.join(str(i).lower() for i in indicators) + ' ' + ml_detection.lower()
            if any(w in combined for w in WEAPON_KEYWORDS):
                return True

    # Check audio detected sounds
    if audio_result:
        for sound in audio_result.get('detected_sounds', []):
            if any(w in sound.lower() for w in ('gun', 'gunshot', 'explosion', 'bomb')):
                return True

    return False


def _score_to_label(score: int) -> str:
    """Map severity score to human-readable label."""
    for threshold, label in SEVERITY_LABELS:
        if score >= threshold:
            return label
    return 'Mild'
