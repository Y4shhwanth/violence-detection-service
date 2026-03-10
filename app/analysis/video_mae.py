"""
VideoMAE Analyzer for Violence Detection System.
Uses MCG-NJU/videomae-base-finetuned-kinetics for action recognition.
Maps Kinetics-400 labels to violence categories.
"""
import numpy as np
import cv2
from typing import Dict, Any, List, Optional

from .base import BaseAnalyzer
from ..config import get_config
from ..models.loader import get_model_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Kinetics-400 labels mapped to violence
VIOLENCE_LABELS = {
    'punching bag': 0.7, 'punching person (boxing)': 0.9,
    'wrestling': 0.6, 'kickboxing': 0.8, 'sword fighting': 0.9,
    'shooting goal (soccer)': 0.1, 'shooting basketball': 0.1,
    'slapping': 0.8, 'headbutting': 0.9, 'drop kicking': 0.8,
    'punching person': 0.9, 'pushing cart': 0.0,
    'fighting': 0.9, 'boxing': 0.7,
    'karate': 0.5, 'judo': 0.5, 'fencing': 0.4,
    'arm wrestling': 0.3, 'tai chi': 0.1,
}

# Keywords in label that suggest violence
VIOLENCE_KEYWORDS = {
    'punch': 0.85, 'kick': 0.8, 'fight': 0.9, 'slap': 0.8,
    'hit': 0.7, 'shoot': 0.6, 'stab': 0.95, 'wrestl': 0.6,
    'box': 0.6, 'attack': 0.9, 'throw': 0.3, 'push': 0.3,
    'headbutt': 0.9, 'choke': 0.9, 'strangle': 0.95,
}


class VideoMAEAnalyzer(BaseAnalyzer):
    """Analyzes video clips using VideoMAE for action recognition."""

    def __init__(self):
        super().__init__()
        self._modality = 'video'

    def analyze(self, video_path: str) -> Dict[str, Any]:
        """Analyze video using VideoMAE model."""
        try:
            frames = self._extract_clip_frames(video_path, num_frames=16)
            if not frames:
                return self._create_error_result('Could not extract frames')

            manager = get_model_manager()
            videomae = manager.videomae_model
            if videomae is None:
                return self._create_error_result('VideoMAE model not loaded')

            processor, model = videomae
            return self._classify_clip(frames, processor, model)

        except Exception as e:
            logger.error(f"VideoMAE analysis failed: {e}")
            return self._create_error_result(str(e))

    def analyze_clips(self, video_path: str, clip_duration: float = 2.0) -> List[Dict[str, Any]]:
        """Analyze multiple clips from the video."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            cap.release()

            clip_results = []
            num_clips = max(1, int(duration / clip_duration))
            num_clips = min(num_clips, 10)  # Cap at 10 clips

            for i in range(num_clips):
                start_time = i * clip_duration
                frames = self._extract_clip_frames(
                    video_path, num_frames=16,
                    start_sec=start_time, end_sec=start_time + clip_duration
                )
                if frames:
                    manager = get_model_manager()
                    videomae = manager.videomae_model
                    if videomae:
                        processor, model = videomae
                        result = self._classify_clip(frames, processor, model)
                        result['clip_start'] = start_time
                        result['clip_end'] = start_time + clip_duration
                        clip_results.append(result)

            return clip_results

        except Exception as e:
            logger.error(f"VideoMAE multi-clip analysis failed: {e}")
            return []

    def _extract_clip_frames(
        self, video_path: str, num_frames: int = 16,
        start_sec: float = 0, end_sec: float = None
    ) -> List[np.ndarray]:
        """Extract evenly-spaced frames for a video clip."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps) if end_sec else total_frames
        end_frame = min(end_frame, total_frames)

        if end_frame <= start_frame:
            cap.release()
            return []

        indices = np.linspace(start_frame, end_frame - 1, num_frames, dtype=int)
        frames = []

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)

        cap.release()
        return frames

    def _classify_clip(self, frames: List[np.ndarray], processor, model) -> Dict[str, Any]:
        """Classify a clip using VideoMAE."""
        import torch

        inputs = processor(list(frames), return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)[0]

        # Get top predictions
        top_k = 5
        top_indices = probs.topk(top_k).indices.tolist()
        top_probs = probs.topk(top_k).values.tolist()

        labels = model.config.id2label
        predictions = []
        violence_score = 0.0

        for idx, prob in zip(top_indices, top_probs):
            label = labels.get(idx, f'label_{idx}').lower()
            predictions.append({'label': label, 'score': float(prob)})

            # Check against violence labels
            if label in VIOLENCE_LABELS:
                violence_score = max(violence_score, prob * VIOLENCE_LABELS[label] * 100)
            else:
                # Check keywords
                for kw, weight in VIOLENCE_KEYWORDS.items():
                    if kw in label:
                        violence_score = max(violence_score, prob * weight * 100)
                        break

        is_violent = violence_score > 40
        return self._create_result(
            is_violent=is_violent,
            confidence=min(100, violence_score) if is_violent else max(0, 100 - violence_score),
            reasoning=f"VideoMAE top action: {predictions[0]['label']} ({predictions[0]['score']*100:.1f}%)",
            action_predictions=predictions,
            violence_score=float(violence_score),
        )


_videomae_analyzer = None


def get_videomae_analyzer() -> VideoMAEAnalyzer:
    global _videomae_analyzer
    if _videomae_analyzer is None:
        _videomae_analyzer = VideoMAEAnalyzer()
    return _videomae_analyzer
