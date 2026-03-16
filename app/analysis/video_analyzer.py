"""
Video content analyzer for Violence Detection System.
Analyzes video frames for violence indicators with optimized frame extraction.
"""
from typing import Dict, Any, List, Optional

from .base import BaseAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.errors import AnalysisError
from ..utils.logging import log_performance


class VideoAnalyzer(BaseAnalyzer):
    """Analyzes video content for violence indicators."""

    def __init__(self):
        super().__init__()
        self._modality = 'video'
        self.config = get_config().video
        self.model_manager = get_model_manager()

    @log_performance('video_analyzer')
    def analyze(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze video content for violence detection.

        Args:
            video_path: Path to video file

        Returns:
            Analysis result dictionary
        """
        import cv2

        try:
            # Fail fast if image classifier couldn't load (e.g. low-memory host)
            if self.model_manager.image_classifier is None:
                return self._create_error_result('Image model not available (insufficient memory)')

            self.logger.info(f"Analyzing video: {video_path}")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return self._create_error_result('Cannot open video')

            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            duration = total_frames / fps

            self.logger.info(
                f"Video properties: frames={total_frames}, duration={duration:.1f}s, fps={fps:.1f}"
            )

            # Use adaptive keyframe selection for better coverage
            from ..utils.performance import get_keyframe_selector
            try:
                selector = get_keyframe_selector(method='adaptive')
                frame_indices = selector.select_keyframes(
                    video_path, target_count=self.config.frame_sample_count
                )
            except Exception:
                frame_indices = None

            # Extract and analyze frames using optimized method
            frame_results = self._extract_and_analyze_frames(
                cap, total_frames, fps, frame_indices
            )
            cap.release()

            if not frame_results:
                return self._create_error_result('No frames analyzed')

            base_result = self._build_result(frame_results, total_frames, fps)

            # Enhanced: integrate VideoMAE when enabled
            use_enhanced = get_config().model.use_enhanced_models
            if use_enhanced:
                base_result = self._integrate_videomae(base_result, video_path)

            return base_result

        except Exception as e:
            self.logger.error(f"Video analysis failed: {e}", exc_info=True)
            raise AnalysisError(
                "Video analysis failed",
                analysis_type='video',
                details={'error': str(e), 'video_path': video_path}
            )

    def _integrate_videomae(self, base_result: Dict[str, Any], video_path: str) -> Dict[str, Any]:
        """Integrate VideoMAE action recognition results (0.6*MAE + 0.4*existing)."""
        try:
            from .video_mae import get_videomae_analyzer
            mae_analyzer = get_videomae_analyzer()
            mae_result = mae_analyzer.analyze(video_path)

            if mae_result.get('class') == 'Error':
                return base_result

            # Blend scores
            base_conf = base_result.get('confidence', 0)
            mae_conf = mae_result.get('confidence', 0)
            base_violent = base_result.get('class') == 'Violence'
            mae_violent = mae_result.get('class') == 'Violence'

            if base_violent and mae_violent:
                blended = 0.4 * base_conf + 0.6 * mae_conf
                base_result['confidence'] = min(100, blended)
            elif mae_violent and not base_violent:
                mae_score = mae_result.get('violence_score', 0)
                if mae_score > 60:
                    base_result['class'] = 'Violence'
                    base_result['confidence'] = mae_conf * 0.6
            elif base_violent and not mae_violent:
                # Reduce confidence slightly if MAE disagrees
                base_result['confidence'] = base_conf * 0.85

            base_result['videomae_result'] = {
                'action': mae_result.get('action_predictions', [])[:3],
                'violence_score': mae_result.get('violence_score', 0),
            }

            self.logger.info(f"VideoMAE integration: blended confidence={base_result['confidence']:.1f}")
            return base_result

        except Exception as e:
            self.logger.warning(f"VideoMAE integration failed (non-fatal): {e}")
            return base_result

    def _extract_and_analyze_frames(
        self,
        cap,
        total_frames: int,
        fps: float,
        precomputed_indices: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract frames using optimized sequential skipping instead of seeking.
        This provides 40-60% speedup over random seeking.
        """
        import numpy as np
        if precomputed_indices is not None:
            frame_indices = np.array(sorted(precomputed_indices), dtype=int)
        else:
            num_samples = min(self.config.frame_sample_count, total_frames)
            frame_indices = np.linspace(0, total_frames - 1, num_samples, dtype=int)

        frame_results = []
        current_frame = 0
        prev_frame = None
        image_classifier = self.model_manager.image_classifier

        for idx, target_frame in enumerate(frame_indices):
            # Skip frames to reach target (more efficient than seeking)
            while current_frame < target_frame:
                cap.grab()  # Fast skip without decoding
                current_frame += 1

            ret, frame = cap.read()
            if not ret:
                continue
            current_frame += 1

            timestamp = target_frame / fps

            # Analyze frame with heuristics (pass prev_frame for motion detection)
            frame_analysis = self._analyze_frame(frame, prev_frame)
            prev_frame = frame.copy()

            frame_info = {
                'frame_number': int(target_frame),
                'timestamp': f"{int(timestamp//60)}:{int(timestamp%60):02d}",
                'timestamp_seconds': float(timestamp),
                'score': max(0, min(100, frame_analysis['score'])),
                'indicators': frame_analysis['indicators'],
                'reasoning': frame_analysis['reasoning']
            }

            # ML analysis on every frame (only 15 frames total)
            if image_classifier:
                ml_result = self._analyze_frame_ml(frame, image_classifier)
                if ml_result:
                    frame_info['ml_detection'] = ml_result['labels']
                    frame_info['ml_score'] = ml_result['score']

            frame_results.append(frame_info)

        return frame_results

    def _analyze_frame(self, frame, prev_frame=None) -> Dict[str, Any]:
        """
        Analyze a single frame for violence indicators.
        Consolidated frame analysis logic (removes duplication from original code).
        """
        import numpy as np
        import cv2
        violence_score = 0
        indicators = []
        reasoning_parts = []

        # 1. Red color intensity (blood indicator)
        red_channel = frame[:, :, 2]
        green_channel = frame[:, :, 1]
        blue_channel = frame[:, :, 0]

        red_intensity = np.mean(red_channel)
        red_dominance = np.mean(red_channel > (green_channel + blue_channel) / 2)

        if red_intensity > self.config.red_intensity_high and red_dominance > self.config.red_dominance_high:
            violence_score += 45
            indicators.append('High red intensity')
            reasoning_parts.append(f"Significant red/blood-like colors (intensity: {red_intensity:.0f})")
        elif red_intensity > self.config.red_intensity_medium and red_dominance > self.config.red_dominance_medium:
            violence_score += 30
            indicators.append('Moderate red')
            reasoning_parts.append(f"Moderate red tones (intensity: {red_intensity:.0f})")

        # 2. Darkness analysis
        brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if brightness < self.config.brightness_very_dark:
            violence_score += 20
            indicators.append('Very dark')
            reasoning_parts.append(f"Dark scene (brightness: {brightness:.0f})")
        elif brightness < self.config.brightness_moderately_dark:
            violence_score += 10
            indicators.append('Moderately dark')

        # 3. Color variance (chaos indicator)
        color_variance = np.std(frame)
        if color_variance > self.config.color_variance_high:
            violence_score += 20
            indicators.append('High chaos')
            reasoning_parts.append(f"Chaotic/varied colors (variance: {color_variance:.0f})")
        elif color_variance > self.config.color_variance_medium:
            violence_score += 10
            indicators.append('Moderate chaos')

        # 4. Edge density (weapons/sharp objects)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        if edge_density > self.config.edge_density_high:
            violence_score += 25
            indicators.append('Many sharp edges')
            reasoning_parts.append(f"Many sharp objects/edges detected ({edge_density:.3f})")
        elif edge_density > self.config.edge_density_medium:
            violence_score += 15
            indicators.append('Some edges')

        # 5. Motion blur detection
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < self.config.motion_blur_threshold:
            violence_score += 10
            indicators.append('Motion blur')
            reasoning_parts.append("Fast motion/blur detected")

        # 6. Inter-frame motion detection (high thresholds to avoid false positives)
        if prev_frame is not None:
            frame_diff = np.mean(np.abs(frame.astype(float) - prev_frame.astype(float)))
            if frame_diff > 70:
                violence_score += 20
                indicators.append('Rapid scene change')
                reasoning_parts.append(f"Rapid motion/scene change detected (diff: {frame_diff:.0f})")
            elif frame_diff > 55:
                violence_score += 10
                indicators.append('Moderate motion')
                reasoning_parts.append(f"Moderate motion detected (diff: {frame_diff:.0f})")

        return {
            'score': min(violence_score, 100),
            'indicators': indicators,
            'reasoning': '; '.join(reasoning_parts) if reasoning_parts else "No significant violence indicators"
        }

    def _analyze_frame_ml(
        self,
        frame,
        classifier
    ) -> Optional[Dict[str, Any]]:
        """Analyze frame using ML image classifier."""
        try:
            import cv2
            import torch
            from PIL import Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            with torch.no_grad():
                results = classifier(pil_image)

            violence_score = 0
            ml_labels = []

            violence_keywords = ['nsfw', 'violence', 'blood', 'weapon', 'explicit']

            for result in results:
                label = result['label'].lower()
                score = result['score']
                if any(word in label for word in violence_keywords):
                    violence_score = max(violence_score, score * 100)
                    ml_labels.append(f"{label}({score*100:.0f}%)")

            if ml_labels and violence_score >= self.config.ml_min_score:
                return {
                    'labels': ', '.join(ml_labels),
                    'score': violence_score
                }
            return None

        except Exception as e:
            self.logger.warning(f"ML frame analysis failed: {e}")
            return None

    def analyze_temporal(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze video with temporal violation detection.
        Returns standard result plus violations list with timestamps.
        """
        from .temporal import VideoTemporalDetector

        result = self.analyze(video_path)

        # Re-extract frame results for temporal detection
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                result['violations'] = []
                return result

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30

            frame_results = self._extract_and_analyze_frames(cap, total_frames, fps)
            cap.release()

            detector = VideoTemporalDetector()
            result['violations'] = detector.detect(frame_results, fps)

        except Exception as e:
            self.logger.error(f"Temporal video analysis failed: {e}")
            result['violations'] = []

        return result

    @staticmethod
    def _spike_aware_combine(avg: float, mx: float) -> float:
        """
        Combine avg and max heuristic scores with spike awareness.
        Safe videos have uniform scores (max ≈ avg) → use avg only.
        Violent videos have spikes (max >> avg) → blend in max.
        """
        if avg > 0 and mx > avg * 1.3:
            # Spike detected — weight max into the score
            return (avg * 0.5) + (mx * 0.5)
        else:
            # Uniform scores — avg alone (prevents false positives)
            return avg

    def _build_result(
        self,
        frame_results: List[Dict[str, Any]],
        total_frames: int,
        fps: float
    ) -> Dict[str, Any]:
        """Build the final analysis result with ML-dominant scoring."""
        import numpy as np
        violence_scores = [f['score'] for f in frame_results]
        ml_scores = [f.get('ml_score', 0) for f in frame_results if 'ml_score' in f]

        avg_heuristic = float(np.mean(violence_scores))
        max_heuristic = float(np.max(violence_scores))

        self.logger.info(f"Heuristic scores: avg={avg_heuristic:.1f}, max={max_heuristic:.1f}")

        # Scoring: ML-dominant when strong ML signal, spike-aware heuristic otherwise
        if ml_scores:
            max_ml = float(np.max(ml_scores))
            self.logger.info(f"ML scores: max={max_ml:.1f}")
            if max_ml >= 50:
                # Strong NSFW/explicit signal → ML-dominant
                combined_score = (avg_heuristic * 0.3) + (max_ml * 0.7)
            else:
                # Weak ML → fall through to heuristic formula
                combined_score = self._spike_aware_combine(avg_heuristic, max_heuristic)
        else:
            # No ML available — spike-aware heuristic (NO CAP)
            combined_score = self._spike_aware_combine(avg_heuristic, max_heuristic)

        # Clamp to 0-100
        combined_score = max(0.0, min(100.0, combined_score))

        # Find most violent frames
        violent_frames = sorted(frame_results, key=lambda x: x['score'], reverse=True)[:3]

        # Violence threshold: configurable, default 40
        violence_threshold = self.config.violence_threshold
        is_violent = combined_score > violence_threshold

        self.logger.info(
            f"Video decision: combined={combined_score:.1f}, threshold={violence_threshold}, "
            f"is_violent={is_violent}"
        )

        # Build reasoning
        reasoning_parts = []
        if is_violent:
            violent_frame_count = len([f for f in frame_results if f['score'] > self.config.frame_violence_threshold])
            reasoning_parts.append(f"Violence detected across {violent_frame_count} frames")

            for vf in violent_frames:
                if vf['score'] > self.config.frame_violence_threshold:
                    reasoning_parts.append(
                        f"[{vf['timestamp']}] Frame #{vf['frame_number']}: {vf['reasoning']} (Score: {vf['score']:.0f})"
                    )

            # Confidence = combined score directly, no artificial boost
            confidence = max(0.0, min(100.0, combined_score))

            # Clean frames for JSON serialization
            violent_frames_clean = [
                {
                    'frame_number': int(vf['frame_number']),
                    'timestamp': vf['timestamp'],
                    'score': int(vf['score']),
                    'indicators': vf['indicators'],
                    'reasoning': vf['reasoning']
                }
                for vf in violent_frames
            ]

            return self._create_result(
                is_violent=True,
                confidence=confidence,
                reasoning=' | '.join(reasoning_parts),
                violent_frames=violent_frames_clean,
                avg_score=avg_heuristic,
                max_score=max_heuristic,
                ml_max_score=float(max(ml_scores)) if ml_scores else 0.0,
                total_frames_analyzed=len(frame_results)
            )
        else:
            return self._create_result(
                is_violent=False,
                confidence=max(0.0, min(100.0, 100 - combined_score)),
                reasoning=f'Low violence indicators across all frames (avg: {avg_heuristic:.1f})',
                avg_score=avg_heuristic,
                max_score=max_heuristic,
                ml_max_score=float(max(ml_scores)) if ml_scores else 0.0,
                total_frames_analyzed=len(frame_results)
            )
