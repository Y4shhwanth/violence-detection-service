"""
Cross-Modal Reasoning Engine for Violence Detection.
Analyzes temporal alignment, semantic consistency, and contradictions across modalities.
"""
from typing import Dict, Any, List, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)


class CrossModalReasoningEngine:
    """Analyzes cross-modal agreement and contradictions."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def analyze(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
        text_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Perform cross-modal reasoning analysis.
        Returns: {cross_modal_score, agreements, contradictions, reasoning}
        """
        agreements = []
        contradictions = []
        reasoning_parts = []

        modalities = {}
        if video_result and video_result.get('class') != 'Error':
            modalities['video'] = video_result
        if audio_result and audio_result.get('class') != 'Error':
            modalities['audio'] = audio_result
        if text_result and text_result.get('class') != 'Error':
            modalities['text'] = text_result

        if len(modalities) < 2:
            return {
                'cross_modal_score': 0,
                'agreements': [],
                'contradictions': [],
                'reasoning': 'Insufficient modalities for cross-modal reasoning',
                'temporal_alignment': None,
            }

        # Check class agreement
        classes = {m: r.get('class', 'Non-Violence') for m, r in modalities.items()}
        violence_modalities = [m for m, c in classes.items() if c == 'Violence']
        non_violence_modalities = [m for m, c in classes.items() if c != 'Violence']

        if len(violence_modalities) >= 2:
            agreements.append({
                'type': 'class_agreement',
                'modalities': violence_modalities,
                'detail': f'{", ".join(violence_modalities)} agree on Violence',
            })
            reasoning_parts.append(f"Agreement: {', '.join(violence_modalities)} detect violence")

        if violence_modalities and non_violence_modalities:
            contradictions.append({
                'type': 'class_contradiction',
                'violent': violence_modalities,
                'non_violent': non_violence_modalities,
                'detail': f'Contradiction: {", ".join(violence_modalities)} vs {", ".join(non_violence_modalities)}',
            })
            reasoning_parts.append(f"Contradiction: {', '.join(violence_modalities)} vs {', '.join(non_violence_modalities)}")

        # Temporal alignment check (do video + audio violence peaks coincide?)
        temporal_alignment = self._check_temporal_alignment(
            modalities.get('video'), modalities.get('audio')
        )
        if temporal_alignment:
            if temporal_alignment['aligned']:
                agreements.append({
                    'type': 'temporal_alignment',
                    'detail': f"Video and audio violence peaks coincide at {temporal_alignment['overlap_segments']}",
                })
                reasoning_parts.append("Temporal alignment: video+audio peaks coincide")
            else:
                reasoning_parts.append("No temporal alignment between video and audio peaks")

        # Semantic consistency: check if text content matches visual/audio evidence
        semantic = self._check_semantic_consistency(modalities)
        if semantic.get('consistent'):
            agreements.append({
                'type': 'semantic_consistency',
                'detail': semantic.get('detail', 'Content semantically consistent'),
            })

        # Calculate cross-modal score
        agreement_boost = len(agreements) * 3
        contradiction_penalty = len(contradictions) * 2
        temporal_boost = 5 if (temporal_alignment and temporal_alignment.get('aligned')) else 0

        cross_modal_score = agreement_boost - contradiction_penalty + temporal_boost

        return {
            'cross_modal_score': cross_modal_score,
            'agreements': agreements,
            'contradictions': contradictions,
            'reasoning': ' | '.join(reasoning_parts) if reasoning_parts else 'No significant cross-modal patterns',
            'temporal_alignment': temporal_alignment,
        }

    def _check_temporal_alignment(
        self,
        video_result: Optional[Dict[str, Any]],
        audio_result: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Check if video and audio violence peaks temporally align."""
        if not video_result or not audio_result:
            return None

        video_violations = video_result.get('violations', [])
        audio_violations = audio_result.get('violations', [])

        if not video_violations or not audio_violations:
            return {'aligned': False, 'overlap_segments': []}

        overlaps = []
        for vv in video_violations:
            v_start = vv.get('start_seconds', 0)
            v_end = vv.get('end_seconds', v_start + 1)

            for av in audio_violations:
                a_start = av.get('start_seconds', 0)
                a_end = av.get('end_seconds', a_start + 1)

                # Check overlap
                overlap_start = max(v_start, a_start)
                overlap_end = min(v_end, a_end)

                if overlap_start < overlap_end:
                    overlaps.append({
                        'start': overlap_start,
                        'end': overlap_end,
                        'video_reason': vv.get('reason', ''),
                        'audio_reason': av.get('reason', ''),
                    })

        return {
            'aligned': len(overlaps) > 0,
            'overlap_segments': overlaps,
            'video_violations': len(video_violations),
            'audio_violations': len(audio_violations),
        }

    def _check_semantic_consistency(self, modalities: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Check semantic consistency across modalities."""
        video = modalities.get('video', {})
        text = modalities.get('text', {})

        # Simple heuristic: if text mentions weapons and video has edge/red indicators
        text_keywords = set()
        for kw in text.get('keywords_found', []):
            text_keywords.add(kw.split('(')[0].strip().lower())

        video_indicators = set()
        for frame in video.get('violent_frames', []):
            for ind in frame.get('indicators', []):
                video_indicators.add(ind.lower())

        weapon_words = {'gun', 'knife', 'weapon', 'bomb', 'explosive'}
        visual_indicators = {'many sharp edges', 'high red intensity', 'rapid scene change'}

        if text_keywords & weapon_words and video_indicators & visual_indicators:
            return {
                'consistent': True,
                'detail': 'Text mentions weapons, video shows sharp edges/red intensity',
            }

        return {'consistent': False}


_reasoning_engine = None


def get_reasoning_engine() -> CrossModalReasoningEngine:
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = CrossModalReasoningEngine()
    return _reasoning_engine
