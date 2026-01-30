"""
Multi-modal fusion for Violence Detection System.
Combines results from text, video, and audio analyzers using parallel processing.
"""
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

from .base import BaseAnalyzer
from .text_analyzer import TextAnalyzer
from .video_analyzer import VideoAnalyzer
from .audio_analyzer import AudioAnalyzer
from ..utils.logging import get_logger, log_performance

logger = get_logger(__name__)


class MultiModalFusion(BaseAnalyzer):
    """
    Combines multiple analysis modalities for comprehensive violence detection.
    Uses parallel processing for 2-3x speedup.
    """

    def __init__(self):
        super().__init__()
        self.text_analyzer = TextAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.audio_analyzer = AudioAnalyzer()

    def analyze(self, content: Any) -> Dict[str, Any]:
        """Not used - use analyze_multimodal instead."""
        raise NotImplementedError("Use analyze_multimodal method")

    @log_performance('multimodal_fusion')
    def analyze_multimodal(
        self,
        video_path: Optional[str] = None,
        text: Optional[str] = None,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze multiple modalities for violence detection.

        Args:
            video_path: Path to video file (optional)
            text: Text content to analyze (optional)
            parallel: Whether to run analyses in parallel (default True)

        Returns:
            Combined analysis results
        """
        results = {
            'success': False,
            'video_prediction': None,
            'audio_prediction': None,
            'text_prediction': None,
            'fused_prediction': None,
            'message': ''
        }

        if parallel:
            results = self._analyze_parallel(video_path, text, results)
        else:
            results = self._analyze_sequential(video_path, text, results)

        # Create fused prediction
        predictions = [
            results['video_prediction'],
            results['audio_prediction'],
            results['text_prediction']
        ]
        valid_predictions = [p for p in predictions if p and p.get('class') != 'Error']

        if valid_predictions:
            results['fused_prediction'] = self._fuse_predictions(valid_predictions)

        results['success'] = True
        results['message'] = 'Analysis completed using pretrained models'

        return results

    def _analyze_parallel(
        self,
        video_path: Optional[str],
        text: Optional[str],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run analyses in parallel using ThreadPoolExecutor.
        Expected 2-3x speedup for combined video+audio+text analysis.
        """
        futures = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit video and audio analysis (can run in parallel)
            if video_path:
                futures['video'] = executor.submit(
                    self._safe_analyze,
                    self.video_analyzer,
                    video_path
                )
                futures['audio'] = executor.submit(
                    self._safe_analyze,
                    self.audio_analyzer,
                    video_path
                )

            # Submit text analysis
            if text:
                futures['text'] = executor.submit(
                    self._safe_analyze,
                    self.text_analyzer,
                    text
                )

            # Collect results
            for name, future in futures.items():
                try:
                    result = future.result(timeout=120)  # 2 minute timeout
                    if name == 'video':
                        results['video_prediction'] = result
                    elif name == 'audio':
                        results['audio_prediction'] = result
                    elif name == 'text':
                        results['text_prediction'] = result
                except Exception as e:
                    logger.error(f"Parallel {name} analysis failed: {e}")

        return results

    def _analyze_sequential(
        self,
        video_path: Optional[str],
        text: Optional[str],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run analyses sequentially (fallback mode)."""
        if video_path:
            results['video_prediction'] = self._safe_analyze(
                self.video_analyzer, video_path
            )
            results['audio_prediction'] = self._safe_analyze(
                self.audio_analyzer, video_path
            )

        if text:
            results['text_prediction'] = self._safe_analyze(
                self.text_analyzer, text
            )

        return results

    def _safe_analyze(
        self,
        analyzer: BaseAnalyzer,
        content: Any
    ) -> Optional[Dict[str, Any]]:
        """Safely run analyzer with error handling."""
        try:
            return analyzer.analyze(content)
        except Exception as e:
            logger.error(f"{analyzer.__class__.__name__} failed: {e}")
            return {
                'class': 'Error',
                'confidence': 0,
                'error': str(e)
            }

    def _fuse_predictions(
        self,
        predictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fuse multiple predictions into a single result.

        Uses majority voting for classification and average confidence.
        """
        violence_count = sum(
            1 for p in predictions
            if p['class'] == 'Violence'
        )
        avg_confidence = float(np.mean([p['confidence'] for p in predictions]))

        # Majority voting
        if violence_count > len(predictions) / 2:
            return {
                'class': 'Violence',
                'confidence': avg_confidence,
                'modalities_detected': violence_count,
                'total_modalities': len(predictions)
            }
        else:
            return {
                'class': 'Non-Violence',
                'confidence': avg_confidence,
                'modalities_detected': violence_count,
                'total_modalities': len(predictions)
            }

    def analyze_video_only(self, video_path: str) -> Dict[str, Any]:
        """Analyze video only (no audio/text)."""
        return self._safe_analyze(self.video_analyzer, video_path)

    def analyze_text_only(self, text: str) -> Dict[str, Any]:
        """Analyze text only."""
        return self._safe_analyze(self.text_analyzer, text)

    def analyze_audio_only(self, video_path: str) -> Dict[str, Any]:
        """Analyze audio only from video file."""
        return self._safe_analyze(self.audio_analyzer, video_path)
