"""
Performance optimization utilities for Violence Detection System.

Includes:
- Keyframe selection (instead of all frames)
- Model optimization hints (FP16, quantization, ONNX)
- Async processing helpers
- Memory management
"""
import numpy as np
import cv2
from typing import List, Tuple, Optional
import torch

from .logging import get_logger

logger = get_logger(__name__)


class KeyframeSelector:
    """
    Intelligent keyframe selection to reduce processing time.
    Instead of analyzing 100+ frames, select 10-15 representative frames.
    """

    def __init__(self, method: str = 'adaptive'):
        """
        Initialize keyframe selector.

        Args:
            method: 'uniform', 'adaptive', or 'scene_change'
        """
        self.method = method
        self.logger = get_logger(__name__)

    def select_keyframes(
        self,
        video_path: str,
        target_count: int = 15,
        max_frames: Optional[int] = None
    ) -> List[int]:
        """
        Select keyframes from video.

        Args:
            video_path: Path to video file
            target_count: Number of keyframes to extract
            max_frames: Maximum frames to consider (for very long videos)

        Returns:
            List of frame indices to analyze
        """
        if self.method == 'uniform':
            return self._select_uniform(video_path, target_count, max_frames)
        elif self.method == 'scene_change':
            return self._select_scene_changes(video_path, target_count, max_frames)
        else:  # adaptive
            return self._select_adaptive(video_path, target_count, max_frames)

    def _select_uniform(
        self,
        video_path: str,
        target_count: int,
        max_frames: Optional[int]
    ) -> List[int]:
        """Simple uniform sampling (current method)."""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        if max_frames and total_frames > max_frames:
            total_frames = max_frames

        return np.linspace(0, total_frames - 1, target_count, dtype=int).tolist()

    def _select_scene_changes(
        self,
        video_path: str,
        target_count: int,
        max_frames: Optional[int]
    ) -> List[int]:
        """
        Select frames based on scene changes.
        More intelligent - focuses on action moments.
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if max_frames and total_frames > max_frames:
            total_frames = max_frames

        # Sample frames for scene change detection
        sample_interval = max(total_frames // 100, 1)  # Check every Nth frame
        scene_changes = [0]  # Always include first frame

        prev_frame = None
        current_frame_idx = 0

        while current_frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_idx)
            ret, frame = cap.read()

            if not ret:
                break

            if prev_frame is not None:
                # Calculate frame difference
                diff = cv2.absdiff(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                )
                diff_score = np.mean(diff)

                # If significant change, mark as scene change
                if diff_score > 30:  # Threshold for scene change
                    scene_changes.append(current_frame_idx)

            prev_frame = frame
            current_frame_idx += sample_interval

        cap.release()

        # Always include last frame
        if scene_changes[-1] != total_frames - 1:
            scene_changes.append(total_frames - 1)

        # If too many scene changes, sample uniformly from them
        if len(scene_changes) > target_count:
            indices = np.linspace(0, len(scene_changes) - 1, target_count, dtype=int)
            return [scene_changes[i] for i in indices]

        # If too few, add uniform samples between them
        if len(scene_changes) < target_count:
            # Fill in gaps with uniform samples
            result = list(scene_changes)
            needed = target_count - len(result)

            for i in range(len(scene_changes) - 1):
                gap_start = scene_changes[i]
                gap_end = scene_changes[i + 1]
                gap_size = gap_end - gap_start

                if gap_size > 1:
                    # Add samples in this gap
                    samples_in_gap = min(needed, gap_size // 2)
                    gap_samples = np.linspace(gap_start + 1, gap_end - 1, samples_in_gap, dtype=int)
                    result.extend(gap_samples)
                    needed -= samples_in_gap

                    if needed <= 0:
                        break

            return sorted(set(result))[:target_count]

        return scene_changes

    def _select_adaptive(
        self,
        video_path: str,
        target_count: int,
        max_frames: Optional[int]
    ) -> List[int]:
        """
        Adaptive sampling: more frames where action happens.
        Uses motion detection to focus on interesting regions.
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if max_frames and total_frames > max_frames:
            total_frames = max_frames

        # Quick pass to detect motion intensity
        sample_interval = max(total_frames // 50, 1)
        motion_scores = []

        prev_frame = None
        for i in range(0, total_frames, sample_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()

            if not ret:
                break

            if prev_frame is not None:
                # Calculate optical flow magnitude (motion)
                gray1 = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                gray2 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Simple motion estimation
                diff = cv2.absdiff(gray1, gray2)
                motion = np.mean(diff)
                motion_scores.append((i, motion))

            prev_frame = frame

        cap.release()

        if not motion_scores:
            # Fallback to uniform
            return self._select_uniform(video_path, target_count, max_frames)

        # Sort by motion (descending)
        motion_scores.sort(key=lambda x: x[1], reverse=True)

        # Select frames: 70% from high-motion, 30% uniform
        high_motion_count = int(target_count * 0.7)
        uniform_count = target_count - high_motion_count

        # High motion frames
        selected = [frame_idx for frame_idx, _ in motion_scores[:high_motion_count]]

        # Add uniform samples
        uniform_frames = np.linspace(0, total_frames - 1, uniform_count, dtype=int).tolist()
        selected.extend(uniform_frames)

        return sorted(set(selected))[:target_count]


class ModelOptimizer:
    """
    Model optimization utilities for faster inference.
    """

    @staticmethod
    def convert_to_fp16(model: torch.nn.Module) -> torch.nn.Module:
        """
        Convert model to FP16 for 2x faster inference.
        Requires CUDA.
        """
        if torch.cuda.is_available():
            model = model.half()
            logger.info("Model converted to FP16")
        else:
            logger.warning("FP16 requires CUDA, skipping")
        return model

    @staticmethod
    def quantize_model(model: torch.nn.Module) -> torch.nn.Module:
        """
        Quantize model to INT8 for 4x faster inference.
        Works on CPU.
        """
        try:
            quantized = torch.quantization.quantize_dynamic(
                model,
                {torch.nn.Linear},
                dtype=torch.qint8
            )
            logger.info("Model quantized to INT8")
            return quantized
        except Exception as e:
            logger.warning(f"Quantization failed: {e}")
            return model

    @staticmethod
    def get_optimization_hints() -> dict:
        """
        Get optimization recommendations based on hardware.
        """
        hints = {
            'device': 'cuda' if torch.cuda.is_available() else 'cpu',
            'recommendations': []
        }

        if torch.cuda.is_available():
            hints['recommendations'].extend([
                'Use FP16 for 2x speedup',
                'Enable CUDA graphs for static models',
                'Use TorchServe for production serving'
            ])
        else:
            hints['recommendations'].extend([
                'Use INT8 quantization for 4x speedup',
                'Convert to ONNX Runtime for better CPU performance',
                'Consider using model distillation'
            ])

        return hints


class MemoryManager:
    """Memory optimization utilities."""

    @staticmethod
    def clear_cache():
        """Clear GPU/CPU cache."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("CUDA cache cleared")

        import gc
        gc.collect()
        logger.info("Python GC completed")

    @staticmethod
    def get_memory_usage() -> dict:
        """Get current memory usage."""
        usage = {
            'device': 'cuda' if torch.cuda.is_available() else 'cpu'
        }

        if torch.cuda.is_available():
            usage['gpu_allocated'] = torch.cuda.memory_allocated() / 1024**3
            usage['gpu_reserved'] = torch.cuda.memory_reserved() / 1024**3

        return usage


# Global instances
_keyframe_selector = None


def get_keyframe_selector(method: str = 'adaptive') -> KeyframeSelector:
    """Get or create keyframe selector."""
    global _keyframe_selector
    if _keyframe_selector is None:
        _keyframe_selector = KeyframeSelector(method=method)
    return _keyframe_selector
