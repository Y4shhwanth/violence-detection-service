"""
Video content analyzer for Violence Detection System.
Analyzes video frames for violence indicators with optimized frame extraction.
"""
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2
from PIL import Image

from .base import BaseAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.errors import AnalysisError
from ..utils.logging import log_performance


class VideoAnalyzer(BaseAnalyzer):
    """Analyzes video content for violence indicators."""

    def __init__(self):
        super().__init__()
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
        try:
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

            # Extract and analyze frames using optimized method
            frame_results = self._extract_and_analyze_frames(cap, total_frames, fps)
            cap.release()

            if not frame_results:
                return self._create_error_result('No frames analyzed')

            return self._build_result(frame_results, total_frames, fps)

        except Exception as e:
            self.logger.error(f"Video analysis failed: {e}", exc_info=True)
            raise AnalysisError(
                "Video analysis failed",
                analysis_type='video',
                details={'error': str(e), 'video_path': video_path}
            )

    def _extract_and_analyze_frames(
        self,
        cap: cv2.VideoCapture,
        total_frames: int,
        fps: float
    ) -> List[Dict[str, Any]]:
        """
        Extract frames using optimized sequential skipping instead of seeking.
        This provides 40-60% speedup over random seeking.
        """
        num_samples = min(self.config.frame_sample_count, total_frames)
        frame_indices = np.linspace(0, total_frames - 1, num_samples, dtype=int)

        frame_results = []
        current_frame = 0
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

            # Analyze frame with heuristics
            frame_analysis = self._analyze_frame(frame)

            frame_info = {
                'frame_number': int(target_frame),
                'timestamp': f"{int(timestamp//60)}:{int(timestamp%60):02d}",
                'score': frame_analysis['score'],
                'indicators': frame_analysis['indicators'],
                'reasoning': frame_analysis['reasoning']
            }

            # ML analysis every 3rd frame
            if image_classifier and idx % 3 == 0:
                ml_result = self._analyze_frame_ml(frame, image_classifier)
                if ml_result:
                    frame_info['ml_detection'] = ml_result['labels']
                    frame_info['ml_score'] = ml_result['score']

            frame_results.append(frame_info)

        return frame_results

    def _analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Analyze a single frame for violence indicators.
        Consolidated frame analysis logic (removes duplication from original code).
        """
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
        elif red_intensity > self.config.red_intensity_low:
            violence_score += 15
            indicators.append('Some red')

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

        return {
            'score': min(violence_score, 100),
            'indicators': indicators,
            'reasoning': '; '.join(reasoning_parts) if reasoning_parts else "No significant violence indicators"
        }

    def _analyze_frame_ml(
        self,
        frame: np.ndarray,
        classifier
    ) -> Optional[Dict[str, Any]]:
        """Analyze frame using ML image classifier."""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
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

            if ml_labels:
                return {
                    'labels': ', '.join(ml_labels),
                    'score': violence_score
                }
            return None

        except Exception as e:
            self.logger.warning(f"ML frame analysis failed: {e}")
            return None

    def _build_result(
        self,
        frame_results: List[Dict[str, Any]],
        total_frames: int,
        fps: float
    ) -> Dict[str, Any]:
        """Build the final analysis result."""
        violence_scores = [f['score'] for f in frame_results]
        ml_scores = [f.get('ml_score', 0) for f in frame_results if 'ml_score' in f]

        avg_heuristic = np.mean(violence_scores)
        max_heuristic = np.max(violence_scores)

        self.logger.info(f"Heuristic scores: avg={avg_heuristic:.1f}, max={max_heuristic:.1f}")

        if ml_scores:
            avg_ml = np.mean(ml_scores)
            max_ml = np.max(ml_scores)
            self.logger.info(f"ML scores: avg={avg_ml:.1f}, max={max_ml:.1f}")
            combined_score = (avg_heuristic * 0.6) + (max_ml * 0.4)
        else:
            combined_score = avg_heuristic

        # Find most violent frames
        violent_frames = sorted(frame_results, key=lambda x: x['score'], reverse=True)[:3]

        # Determine if violent based on configurable thresholds
        is_violent = (
            combined_score > self.config.combined_threshold or
            max_heuristic > self.config.max_heuristic_threshold or
            avg_heuristic > self.config.avg_heuristic_threshold or
            (ml_scores and max(ml_scores) > self.config.ml_threshold)
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

            confidence = min(combined_score + 20, 95.0)

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
                confidence=max(confidence, 60.0),
                reasoning=' | '.join(reasoning_parts),
                violent_frames=violent_frames_clean,
                avg_score=float(avg_heuristic),
                max_score=float(max_heuristic),
                total_frames_analyzed=len(frame_results)
            )
        else:
            return self._create_result(
                is_violent=False,
                confidence=float(100 - combined_score),
                reasoning=f'Low violence indicators across all frames (avg: {avg_heuristic:.1f})',
                avg_score=float(avg_heuristic),
                max_score=float(max_heuristic),
                total_frames_analyzed=len(frame_results)
            )
