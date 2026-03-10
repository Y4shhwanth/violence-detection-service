"""
Temporal violation detection for Violence Detection System.

Provides per-segment and per-sentence violation detection with precise timestamps,
replacing whole-video verdicts with actionable violation windows.
"""
import re
from typing import Dict, Any, List, Optional

import numpy as np

from ..utils.logging import get_logger

logger = get_logger(__name__)


class VideoTemporalDetector:
    """
    Groups consecutive violent frames into violation segments with timestamps.
    Merges segments closer than a configurable gap (default 1s).
    """

    def __init__(self, threshold: int = 30, merge_gap: float = 1.0):
        self.threshold = threshold
        self.merge_gap = merge_gap

    def detect(
        self,
        frame_results: List[Dict[str, Any]],
        fps: float
    ) -> List[Dict[str, Any]]:
        """
        Detect temporal violation segments from per-frame results.

        Args:
            frame_results: List of frame analysis dicts with 'score', 'timestamp_seconds', etc.
            fps: Video frames per second.

        Returns:
            List of violation segment dicts.
        """
        if not frame_results:
            return []

        # Find frames exceeding threshold
        violent_frames = [
            f for f in frame_results
            if f.get('score', 0) > self.threshold
        ]

        if not violent_frames:
            return []

        # Sort by timestamp
        violent_frames.sort(key=lambda f: f.get('timestamp_seconds', 0))

        # Group into segments
        segments = []
        current_segment = {
            'frames': [violent_frames[0]],
            'start_time': violent_frames[0].get('timestamp_seconds', 0),
            'end_time': violent_frames[0].get('timestamp_seconds', 0),
        }

        for frame in violent_frames[1:]:
            frame_time = frame.get('timestamp_seconds', 0)
            if frame_time - current_segment['end_time'] <= self.merge_gap:
                current_segment['frames'].append(frame)
                current_segment['end_time'] = frame_time
            else:
                segments.append(current_segment)
                current_segment = {
                    'frames': [frame],
                    'start_time': frame_time,
                    'end_time': frame_time,
                }

        segments.append(current_segment)

        # Build violation objects
        violations = []
        for seg in segments:
            scores = [f['score'] for f in seg['frames']]
            peak_score = max(scores)
            avg_score = np.mean(scores)

            # Determine type from indicators
            all_indicators = []
            for f in seg['frames']:
                all_indicators.extend(f.get('indicators', []))

            violation_type = self._classify_type(all_indicators)
            severity = self._score_to_severity(peak_score)

            # Build reason from top indicators
            indicator_counts = {}
            for ind in all_indicators:
                indicator_counts[ind] = indicator_counts.get(ind, 0) + 1
            top_indicators = sorted(indicator_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            reason = ', '.join(f"{ind}" for ind, _ in top_indicators)

            violations.append({
                'type': violation_type,
                'modality': 'video',
                'start_time': self._format_time(seg['start_time']),
                'end_time': self._format_time(seg['end_time']),
                'start_seconds': float(seg['start_time']),
                'end_seconds': float(seg['end_time']),
                'peak_score': float(peak_score),
                'avg_score': float(avg_score),
                'frame_count': len(seg['frames']),
                'reason': reason or 'Visual violence indicators detected',
                'severity': severity,
            })

        return violations

    def _classify_type(self, indicators: List[str]) -> str:
        indicator_str = ' '.join(indicators).lower()
        if 'weapon' in indicator_str or 'sharp' in indicator_str or 'edge' in indicator_str:
            return 'weapon_violence'
        if 'red' in indicator_str or 'blood' in indicator_str:
            return 'graphic_violence'
        if 'motion' in indicator_str or 'blur' in indicator_str:
            return 'physical_violence'
        return 'visual_violence'

    def _score_to_severity(self, score: float) -> str:
        if score >= 80:
            return 'Critical'
        if score >= 60:
            return 'Severe'
        if score >= 40:
            return 'Moderate'
        return 'Mild'

    @staticmethod
    def _format_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


class AudioTemporalDetector:
    """
    Splits audio into windowed segments and detects violence per window.
    """

    def __init__(self, window_size: float = 3.0, overlap: float = 1.0):
        self.window_size = window_size
        self.overlap = overlap

    def detect(
        self,
        audio: 'np.ndarray',
        sr: int,
        classifier,
        sound_weights: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """
        Detect temporal audio violations using windowed classification.

        Args:
            audio: Audio signal array.
            sr: Sample rate.
            classifier: Audio classification pipeline.
            sound_weights: Violence keyword weights.

        Returns:
            List of audio violation dicts.
        """
        import torch

        if classifier is None or len(audio) == 0:
            return []

        violations = []
        total_duration = len(audio) / sr
        step = self.window_size - self.overlap
        position = 0.0

        while position < total_duration:
            end = min(position + self.window_size, total_duration)
            start_sample = int(position * sr)
            end_sample = int(end * sr)

            window = audio[start_sample:end_sample]
            if len(window) < sr * 0.5:  # Skip windows shorter than 0.5s
                break

            try:
                with torch.no_grad():
                    results = classifier(window, sampling_rate=sr, top_k=5)

                violence_score = 0
                detected_sounds = []

                for result in results:
                    label = result['label'].lower()
                    score = result['score'] * 100

                    for keyword, weight in sound_weights.items():
                        if keyword in label:
                            weighted = (score * weight) / 100
                            violence_score += weighted
                            detected_sounds.append(f"{label} ({score:.0f}%)")
                            break

                if violence_score > 20 or detected_sounds:
                    severity = 'Critical' if violence_score > 60 else (
                        'Severe' if violence_score > 40 else 'Moderate'
                    )
                    violations.append({
                        'type': 'violent_audio',
                        'modality': 'audio',
                        'start_time': VideoTemporalDetector._format_time(position),
                        'end_time': VideoTemporalDetector._format_time(end),
                        'start_seconds': float(position),
                        'end_seconds': float(end),
                        'peak_score': float(violence_score),
                        'detected_sounds': detected_sounds,
                        'reason': ', '.join(detected_sounds[:3]) or 'Violence-related audio detected',
                        'severity': severity,
                    })

            except Exception as e:
                logger.warning(f"Audio window analysis failed at {position:.1f}s: {e}")

            position += step

        # Merge adjacent violations
        return self._merge_adjacent(violations)

    def _merge_adjacent(self, violations: List[Dict]) -> List[Dict]:
        if len(violations) <= 1:
            return violations

        merged = [violations[0]]
        for v in violations[1:]:
            prev = merged[-1]
            if v['start_seconds'] - prev['end_seconds'] <= self.overlap:
                prev['end_time'] = v['end_time']
                prev['end_seconds'] = v['end_seconds']
                prev['peak_score'] = max(prev['peak_score'], v['peak_score'])
                prev['detected_sounds'] = list(set(
                    prev.get('detected_sounds', []) + v.get('detected_sounds', [])
                ))[:5]
                prev['reason'] = ', '.join(prev['detected_sounds'][:3])
            else:
                merged.append(v)
        return merged


class TextTemporalDetector:
    """
    Splits text into sentences and classifies each individually.
    """

    def detect(
        self,
        text: str,
        classifier,
        violence_keywords: Dict[str, List[str]],
        config
    ) -> List[Dict[str, Any]]:
        """
        Detect per-sentence text violations.

        Args:
            text: Full text input.
            classifier: Text classification pipeline.
            violence_keywords: Violence keyword categories.
            config: TextAnalysisConfig.

        Returns:
            List of text violation dicts.
        """
        import torch

        if not text or not text.strip():
            return []

        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        if not sentences:
            return []

        violations = []

        for idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) < 3:
                continue

            # Check keywords
            sentence_lower = sentence.lower()
            found_keywords = []
            keyword_score = 0

            for category, words in violence_keywords.items():
                for word in words:
                    if word in sentence_lower:
                        found_keywords.append(f"{word} ({category})")
                        if category == 'extreme':
                            keyword_score += 35
                        elif category == 'physical':
                            keyword_score += 25
                        else:
                            keyword_score += 15

            # ML classification
            ml_violent = False
            ml_confidence = 0
            try:
                with torch.no_grad():
                    result = classifier(sentence[:512])[0]
                label = result['label'].lower()
                score = result['score'] * 100
                ml_confidence = score
                ml_violent = (
                    (label == 'toxic' and score > config.ml_toxic_threshold) or
                    (label == 'negative' and score > config.ml_negative_threshold)
                )
            except Exception:
                pass

            is_violent = keyword_score > config.keyword_threshold or ml_violent or len(found_keywords) > 0

            if is_violent:
                confidence = max(keyword_score, ml_confidence) if found_keywords else ml_confidence
                severity = 'Critical' if confidence > 80 else (
                    'Severe' if confidence > 60 else 'Moderate'
                )
                reason = ', '.join(found_keywords[:3]) if found_keywords else 'Toxic language detected'

                violations.append({
                    'type': 'violent_text',
                    'modality': 'text',
                    'sentence': sentence,
                    'sentence_index': idx,
                    'confidence': float(max(0, min(100, confidence))),
                    'reason': reason,
                    'severity': severity,
                    'keywords': found_keywords,
                })

        return violations
