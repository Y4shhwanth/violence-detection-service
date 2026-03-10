"""
Audio content analyzer for Violence Detection System.
Extracts and analyzes audio from video for violence indicators.
Uses ffmpeg subprocess for optimized audio extraction (3-5x faster than moviepy).
"""
import os
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

import numpy as np
import librosa
import torch

from .base import BaseAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.errors import AnalysisError
from ..utils.logging import log_performance


class AudioAnalyzer(BaseAnalyzer):
    """Analyzes audio content for violence indicators."""

    def __init__(self):
        super().__init__()
        self._modality = 'audio'
        self.config = get_config().audio
        self.model_manager = get_model_manager()

    @log_performance('audio_analyzer')
    def analyze(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze audio content from video for violence detection.

        Args:
            video_path: Path to video file

        Returns:
            Analysis result dictionary
        """
        # Use enhanced analyzer when enabled
        config = get_config()
        if config.model.use_enhanced_models:
            try:
                from .enhanced_audio import EnhancedAudioAnalyzer
                enhanced = EnhancedAudioAnalyzer()
                return enhanced.analyze(video_path)
            except Exception as e:
                self.logger.warning(f"Enhanced audio failed, falling back: {e}")

        return self._analyze_base(video_path)

    def _analyze_base(self, video_path: str) -> Dict[str, Any]:
        """Base audio analysis (original implementation)."""
        audio_classifier = self.model_manager.audio_classifier
        if not audio_classifier:
            return self._create_error_result('Audio model not loaded')

        try:
            self.logger.info(f"Extracting audio from: {video_path}")

            # Extract audio using optimized ffmpeg method
            with self._extract_audio_ffmpeg(video_path) as audio_path:
                if audio_path is None:
                    return self._create_result(
                        is_violent=False,
                        confidence=100.0,
                        reasoning='No audio track found in video'
                    )

                # Load and analyze audio
                audio, sr = librosa.load(
                    audio_path,
                    sr=self.config.sample_rate,
                    duration=self.config.audio_duration_seconds
                )

                # Analyze with ML model (deterministic inference)
                with torch.no_grad():
                    ml_results = audio_classifier(audio, sampling_rate=sr, top_k=10)

                # Check for violence-related sounds
                violence_score, detected_sounds, reasoning_parts = self._analyze_sounds(ml_results)

                # Analyze audio features
                feature_score, feature_reasoning = self._analyze_audio_features(audio)
                violence_score += feature_score
                reasoning_parts.extend(feature_reasoning)

                return self._build_result(violence_score, detected_sounds, reasoning_parts)

        except Exception as e:
            self.logger.error(f"Audio analysis failed: {e}", exc_info=True)
            raise AnalysisError(
                "Audio analysis failed",
                analysis_type='audio',
                details={'error': str(e), 'video_path': video_path}
            )

    @contextmanager
    def _extract_audio_ffmpeg(self, video_path: str):
        """
        Extract audio using ffmpeg subprocess (3-5x faster than moviepy).
        Uses context manager for automatic cleanup.
        """
        audio_path = None
        try:
            # Create temp file for audio
            fd, audio_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)

            # Use ffmpeg for fast extraction
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', str(self.config.sample_rate),
                '-ac', '1',  # Mono
                '-t', str(self.config.audio_duration_seconds),  # Duration limit
                audio_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30
            )

            if result.returncode != 0:
                # Check if it's a "no audio" error
                stderr = result.stderr.decode()
                if 'does not contain any stream' in stderr or 'no audio' in stderr.lower():
                    self.logger.info("Video has no audio track")
                    yield None
                    return

                self.logger.warning(f"ffmpeg extraction failed, trying fallback: {stderr}")
                # Try fallback with moviepy
                yield self._extract_audio_moviepy(video_path)
                return

            yield audio_path

        except subprocess.TimeoutExpired:
            self.logger.warning("ffmpeg timeout, trying fallback")
            yield self._extract_audio_moviepy(video_path)

        except FileNotFoundError:
            self.logger.warning("ffmpeg not found, using moviepy fallback")
            yield self._extract_audio_moviepy(video_path)

        finally:
            # Cleanup temp file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except OSError as e:
                    self.logger.warning(f"Failed to cleanup audio temp file: {e}")

    def _extract_audio_moviepy(self, video_path: str) -> Optional[str]:
        """Fallback audio extraction using moviepy."""
        try:
            from moviepy import VideoFileClip

            audio_path = video_path.replace('.mp4', '_audio.wav')
            video_clip = VideoFileClip(video_path)

            if video_clip.audio is None:
                video_clip.close()
                return None

            video_clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
            video_clip.close()
            return audio_path

        except Exception as e:
            self.logger.error(f"Moviepy fallback failed: {e}")
            return None

    def _analyze_sounds(self, ml_results: List[Dict]) -> tuple:
        """Analyze ML classification results for violence-related sounds."""
        violence_score = 0
        detected_sounds = []
        reasoning_parts = []

        sound_weights = self.config.sound_weights

        for result in ml_results:
            label = result['label'].lower()
            score = result['score'] * 100

            # Check if label contains violence-related keywords
            for keyword, weight in sound_weights.items():
                if keyword in label:
                    weighted_score = (score * weight) / 100
                    violence_score += weighted_score
                    detected_sounds.append(f"{label} ({score:.1f}%)")
                    reasoning_parts.append(f"Detected '{label}' with {score:.1f}% confidence")
                    break

        return violence_score, detected_sounds, reasoning_parts

    def _analyze_audio_features(self, audio: np.ndarray) -> tuple:
        """Analyze audio features for violence indicators."""
        feature_score = 0
        reasoning_parts = []

        # Loudness analysis (violence often has high amplitude spikes)
        rms = librosa.feature.rms(y=audio)[0]
        loudness_spikes = np.sum(rms > np.mean(rms) + 2 * np.std(rms))

        if loudness_spikes > self.config.loudness_spike_threshold:
            feature_score += 20
            reasoning_parts.append(f"Detected {loudness_spikes} loud spikes (possible screams/impacts)")

        # Zero-crossing rate (measures noisiness)
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        if np.mean(zcr) > self.config.zcr_threshold:
            feature_score += 15
            reasoning_parts.append("High audio chaos/noisiness detected")

        return feature_score, reasoning_parts

    def analyze_temporal(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze audio with temporal violation detection (windowed classification).
        Returns standard result plus violations list with timestamps.
        """
        from .temporal import AudioTemporalDetector

        result = self.analyze(video_path)

        try:
            with self._extract_audio_ffmpeg(video_path) as audio_path:
                if audio_path is None:
                    result['violations'] = []
                    return result

                audio, sr = librosa.load(
                    audio_path,
                    sr=self.config.sample_rate,
                    duration=self.config.audio_duration_seconds
                )

                audio_classifier = self.model_manager.audio_classifier
                detector = AudioTemporalDetector()
                result['violations'] = detector.detect(
                    audio, sr, audio_classifier, self.config.sound_weights
                )

        except Exception as e:
            self.logger.error(f"Temporal audio analysis failed: {e}")
            result['violations'] = []

        return result

    def _build_result(
        self,
        violence_score: float,
        detected_sounds: List[str],
        reasoning_parts: List[str]
    ) -> Dict[str, Any]:
        """Build the final analysis result."""
        is_violent = violence_score > self.config.violence_threshold or len(detected_sounds) > 0

        if is_violent:
            final_confidence = min(
                violence_score + self.config.confidence_boost,
                self.config.max_confidence
            )
            reasoning = ' | '.join(reasoning_parts) if reasoning_parts else 'Violence-related sounds detected'

            return self._create_result(
                is_violent=True,
                confidence=max(0, min(100, max(final_confidence, self.config.min_confidence))),
                reasoning=reasoning,
                detected_sounds=detected_sounds[:5],
                violence_score=float(max(0, min(100, violence_score)))
            )
        else:
            return self._create_result(
                is_violent=False,
                confidence=max(0, min(100, max(100 - violence_score, self.config.min_confidence))),
                reasoning='No significant violence-related sounds detected',
                detected_sounds=[],
                violence_score=float(max(0, min(100, violence_score)))
            )
