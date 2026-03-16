"""
Explainability module for Violence Detection System.

Transforms predictions into trustworthy, interpretable outputs with:
- Top contributing factors
- Timeline of events (from real temporal violations)
- Confidence breakdown
- Visual/Audio/Text evidence
- Risk level, compliance suggestion, and flagged keywords
"""
from typing import Dict, Any, List, Optional

from .logging import get_logger

logger = get_logger(__name__)


class ExplainabilityEngine:
    """
    Generates detailed explanations for violence detection predictions.
    Makes the system transparent and trustworthy.
    """

    def __init__(self):
        self.logger = get_logger(__name__)

    def generate_explanation(
        self,
        fused_prediction: Dict[str, Any],
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]],
        violations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive explanation for the prediction.

        Args:
            fused_prediction: Fused prediction result.
            video: Video analysis result.
            audio: Audio analysis result.
            text: Text analysis result.
            violations: List of temporal violations from all modalities.

        Returns:
            Structured explanation dict.
        """
        is_violent = fused_prediction.get('class') == 'Violence'
        violence_prob = fused_prediction.get('violence_probability',
                                              fused_prediction.get('confidence', 0) / 100)
        confidence = fused_prediction.get('confidence', 0)
        violations = violations or []

        # Generate top factors
        top_factors = self._extract_top_factors(fused_prediction, video, audio, text)

        # Generate timeline from real violations
        timeline = self._generate_timeline(video, audio, violations)

        # Confidence breakdown
        confidence_breakdown = self._generate_confidence_breakdown(
            fused_prediction, video, audio, text
        )

        # Modality contributions
        modality_contributions = self._calculate_modality_contributions(
            fused_prediction, video, audio, text
        )

        # Evidence details
        evidence = self._collect_evidence(video, audio, text)

        # Which modalities triggered
        which_modality = []
        if video and video.get('class') == 'Violence':
            which_modality.append('video')
        if audio and audio.get('class') == 'Violence':
            which_modality.append('audio')
        if text and text.get('class') == 'Violence':
            which_modality.append('text')

        # Keywords from text
        keywords = []
        if text and text.get('keywords_found'):
            keywords = [k.split(' (')[0] for k in text['keywords_found'][:10]]

        # Flagged frames
        flagged_frames = []
        if video and video.get('violent_frames'):
            for f in video['violent_frames']:
                flagged_frames.append({
                    'frame_number': f.get('frame_number'),
                    'timestamp': f.get('timestamp'),
                    'score': f.get('score', 0),
                })

        # Risk level
        risk_level = self._determine_risk_level(confidence)

        # Why flagged
        why_flagged = self._generate_why_flagged(which_modality, video, audio, text, violations)

        # Compliance suggestion
        compliance_suggestion = self._generate_compliance_suggestion(is_violent, violations)

        # Summary
        summary = self._generate_summary(is_violent, confidence, which_modality, violations)

        return {
            # Core prediction
            "violence_detected": is_violent,
            "violence_probability": float(violence_prob),
            "confidence_score": float(confidence),

            # Structured fields
            "summary": summary,
            "why_flagged": why_flagged,
            "which_modality": which_modality,
            "keywords": keywords,
            "flagged_frames": flagged_frames,
            "risk_level": risk_level,
            "compliance_suggestion": compliance_suggestion,

            # Explainability
            "top_factors": top_factors,
            "timeline": timeline,
            "confidence_breakdown": confidence_breakdown,
            "modality_contributions": modality_contributions,

            # Evidence
            "evidence": evidence,

            # Metadata
            "fusion_method": fused_prediction.get('fusion_method', 'unknown'),
            "false_positive_check": fused_prediction.get('false_positive_check', 'not_run'),
            "violations_count": len(violations),
        }

    def _determine_risk_level(self, confidence: float) -> str:
        if confidence >= 80:
            return 'Critical'
        if confidence >= 60:
            return 'High'
        if confidence >= 40:
            return 'Medium'
        return 'Low'

    def _generate_summary(
        self,
        is_violent: bool,
        confidence: float,
        which_modality: List[str],
        violations: List[Dict]
    ) -> str:
        if not is_violent:
            return "No significant violence indicators detected. This content appears safe."

        modality_str = ', '.join(which_modality) if which_modality else 'unknown'
        violation_count = len(violations)

        summary = f"Violence detected via {modality_str} analysis with {confidence:.1f}% confidence."
        if violation_count > 0:
            summary += f" Found {violation_count} violation segment(s)."
        return summary

    def _generate_why_flagged(
        self,
        which_modality: List[str],
        video: Optional[Dict],
        audio: Optional[Dict],
        text: Optional[Dict],
        violations: List[Dict]
    ) -> str:
        if not which_modality:
            return "Content was not flagged."

        parts = []
        if 'video' in which_modality and video:
            reason = video.get('reasoning', 'Visual violence indicators detected')
            parts.append(f"Video: {reason}")
        if 'audio' in which_modality and audio:
            sounds = audio.get('detected_sounds', [])
            if sounds:
                parts.append(f"Audio: Detected {', '.join(sounds[:3])}")
            else:
                parts.append(f"Audio: {audio.get('reasoning', 'Violence-related audio detected')}")
        if 'text' in which_modality and text:
            keywords = text.get('keywords_found', [])
            if keywords:
                parts.append(f"Text: Found keywords {', '.join(keywords[:3])}")
            else:
                parts.append(f"Text: {text.get('reasoning', 'Toxic language detected')}")

        return ' | '.join(parts)

    def _generate_compliance_suggestion(
        self,
        is_violent: bool,
        violations: List[Dict]
    ) -> str:
        if not is_violent:
            return "This video complies with community guidelines."

        video_violations = [v for v in violations if v.get('modality') == 'video']
        if video_violations:
            segments = [f"{v['start_time']}-{v['end_time']}" for v in video_violations]
            return f"Remove or blur segment(s) {', '.join(segments)} to comply with content policy."

        audio_violations = [v for v in violations if v.get('modality') == 'audio']
        if audio_violations:
            segments = [f"{v['start_time']}-{v['end_time']}" for v in audio_violations]
            return f"Mute audio in segment(s) {', '.join(segments)}."

        text_violations = [v for v in violations if v.get('modality') == 'text']
        if text_violations:
            return f"Revise {len(text_violations)} flagged sentence(s) to comply with content policy."

        return "Review and edit flagged content to comply with community guidelines."

    def _extract_top_factors(
        self,
        fused: Dict[str, Any],
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Extract top contributing factors for the prediction."""
        factors = []

        # Video factors
        if video and video.get('class') == 'Violence':
            violent_frames = video.get('violent_frames', [])
            for frame in violent_frames[:3]:
                indicators = frame.get('indicators', [])
                if 'High red intensity' in indicators:
                    factors.append("High red intensity detected (potential blood)")
                if 'Many sharp edges' in indicators:
                    factors.append("Sharp objects/edges detected")
                if 'Very dark' in indicators:
                    factors.append("Dark scene detected")
                if 'Motion blur' in indicators:
                    factors.append("Fast motion/blur detected")

        # Audio factors
        if audio and audio.get('class') == 'Violence':
            detected_sounds = audio.get('detected_sounds', [])
            for sound in detected_sounds[:3]:
                factors.append(f"Audio: {sound}")

        # Text factors
        if text and text.get('class') == 'Violence':
            keywords = text.get('keywords_found', [])
            if keywords:
                extreme = [k for k in keywords if 'extreme' in k.lower()]
                if extreme:
                    factors.append(f"Extreme violence keywords: {', '.join(extreme[:3])}")
                else:
                    factors.append(f"Violence keywords detected: {', '.join(keywords[:3])}")

        # Fusion factors
        if fused.get('fusion_method') == 'weighted':
            if fused.get('cross_modal_adjustment', 0) > 0:
                factors.append("Cross-modal agreement boosted confidence")

        return factors[:10]

    def _generate_timeline(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        violations: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Generate timeline from real temporal violations."""
        timeline = []

        if violations:
            for v in violations:
                entry = {
                    'modality': v.get('modality', 'unknown'),
                    'severity': v.get('severity', 'medium'),
                }
                if 'start_time' in v:
                    entry['timestamp'] = v['start_time']
                    entry['seconds'] = v.get('start_seconds', 0)
                    entry['end_timestamp'] = v.get('end_time')
                    entry['events'] = [v.get('reason', 'violation detected')]
                elif 'sentence_index' in v:
                    entry['timestamp'] = f"sentence_{v['sentence_index']}"
                    entry['seconds'] = 0
                    entry['events'] = [v.get('reason', 'text violation')]
                timeline.append(entry)

            timeline.sort(key=lambda x: x.get('seconds', 0))
            return timeline

        # Fallback: build from video frames and audio
        if video and 'violent_frames' in video:
            for frame in video['violent_frames']:
                indicators = frame.get('indicators', [])
                events = []
                if 'High red intensity' in indicators:
                    events.append('blood-like visual')
                if 'Many sharp edges' in indicators:
                    events.append('sharp objects detected')
                if events:
                    timeline.append({
                        'timestamp': frame.get('timestamp', '0:00'),
                        'seconds': frame.get('timestamp_seconds', 0),
                        'events': events,
                        'modality': 'video',
                        'severity': 'high' if len(events) >= 2 else 'medium'
                    })

        timeline.sort(key=lambda x: x.get('seconds', 0))
        return timeline

    def _generate_confidence_breakdown(
        self,
        fused: Dict[str, Any],
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Break down confidence into components."""
        breakdown = {
            'final_confidence': float(fused.get('confidence', 0)),
            'violence_probability': float(fused.get('violence_probability', 0)),
            'components': {}
        }

        if video and video.get('class') != 'Error':
            breakdown['components']['video'] = {
                'confidence': float(video.get('confidence', 0)),
                'score': float(video.get('max_score', 0)),
            }

        if audio and audio.get('class') != 'Error':
            breakdown['components']['audio'] = {
                'confidence': float(audio.get('confidence', 0)),
                'score': float(audio.get('violence_score', 0))
            }

        if text and text.get('class') != 'Error':
            breakdown['components']['text'] = {
                'confidence': float(text.get('confidence', 0)),
                'score': float(text.get('ml_score', 0))
            }

        breakdown['fusion_factors'] = {
            'fusion_method': fused.get('fusion_method', 'unknown'),
            'modality_weights': fused.get('modality_weights', {}),
            'calibrated_scores': fused.get('calibrated_scores', {}),
        }

        return breakdown

    def _calculate_modality_contributions(
        self,
        fused: Dict[str, Any],
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate percentage contribution of each modality."""
        if 'modality_weights' in fused:
            weights = fused['modality_weights']
            return {k: float(v * 100) for k, v in weights.items()}
        return {}

    def _collect_evidence(
        self,
        video: Optional[Dict[str, Any]],
        audio: Optional[Dict[str, Any]],
        text: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Collect detailed evidence from each modality."""
        evidence = {}

        if video and video.get('class') == 'Violence':
            evidence['video'] = {
                'violent_segments': len(video.get('violent_frames', [])),
                'max_violence_score': float(video.get('max_score', 0)),
                'key_frames': [
                    {
                        'timestamp': f['timestamp'],
                        'score': f['score'],
                        'indicators': f['indicators']
                    }
                    for f in video.get('violent_frames', [])[:3]
                ]
            }

        if audio and audio.get('class') == 'Violence':
            evidence['audio'] = {
                'detected_sounds': audio.get('detected_sounds', []),
                'violence_score': float(audio.get('violence_score', 0)),
            }

        if text and text.get('class') == 'Violence':
            evidence['text'] = {
                'keywords_found': text.get('keywords_found', []),
            }

        return evidence


# Global instance
_explainability_engine = None


def get_explainability_engine() -> ExplainabilityEngine:
    """Get or create global explainability engine."""
    global _explainability_engine
    if _explainability_engine is None:
        _explainability_engine = ExplainabilityEngine()
    return _explainability_engine
