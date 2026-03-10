"""Analysis modules for Violence Detection System."""
from .text_analyzer import TextAnalyzer
from .video_analyzer import VideoAnalyzer
from .audio_analyzer import AudioAnalyzer
from .fusion import MultiModalFusion
from .severity import compute_severity

# EmbeddingFusion imports torch/cv2/PIL at module level which is heavy.
# Keep it lazy — imported on first use via get_embedding_fusion().
# Temporal, calibration also lazy.
__all__ = [
    'TextAnalyzer',
    'VideoAnalyzer',
    'AudioAnalyzer',
    'MultiModalFusion',
    'compute_severity',
]

# Enhanced modules (lazy imports - loaded only when USE_ENHANCED_MODELS=True)
# - video_mae.py: VideoMAE action recognition
# - enhanced_audio.py: AST + emotion ensemble
# - enhanced_text.py: ToxicBERT + RoBERTa-offensive ensemble
# - context_detector.py: Sports/gaming/movie/news context detection
# - reasoning_engine.py: Cross-modal reasoning
# - event_detector.py: Unified violence event detection
