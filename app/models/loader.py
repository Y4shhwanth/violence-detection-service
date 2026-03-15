"""
Lazy model loading and management for Violence Detection System.
Models are loaded on first use and cached, eliminating startup time.
"""
import time
from typing import Optional, Any
from threading import Lock

from ..config import get_config
from ..utils.logging import get_logger
from ..utils.errors import ModelError
from ..utils.deterministic import set_deterministic

logger = get_logger(__name__)


class ModelManager:
    """
    Singleton manager for ML models with lazy loading support.
    Models are loaded on first access and optionally cached with TTL.
    """

    _instance: Optional['ModelManager'] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config = get_config().model
        import torch
        self._device = 0 if torch.cuda.is_available() else -1

        # Model storage
        self._text_classifier = None
        self._image_classifier = None
        self._audio_classifier = None

        # Track models that failed to load (don't retry)
        self._text_failed = False
        self._image_failed = False
        self._audio_failed = False

        # Loading timestamps for TTL
        self._text_loaded_at: Optional[float] = None
        self._image_loaded_at: Optional[float] = None
        self._audio_loaded_at: Optional[float] = None

        # Individual locks for thread-safe lazy loading
        self._text_lock = Lock()
        self._image_lock = Lock()
        self._audio_lock = Lock()

        # Enhanced models (Phase 2)
        self._videomae_model = None
        self._emotion_classifier = None
        self._offensive_classifier = None
        self._zero_shot_classifier = None

        self._videomae_lock = Lock()
        self._emotion_lock = Lock()
        self._offensive_lock = Lock()
        self._zero_shot_lock = Lock()

        self._initialized = True

        # Ensure deterministic inference
        set_deterministic()

        device = 'cuda' if self._device == 0 else 'cpu'
        logger.info(f"ModelManager initialized - device={device}, lazy_load={self.config.lazy_load}")

        # If not lazy loading, load models immediately
        if not self.config.lazy_load:
            self.load_all_models()

    def _is_expired(self, loaded_at: Optional[float]) -> bool:
        """Check if a model has expired based on TTL."""
        if self.config.cache_ttl == 0 or loaded_at is None:
            return False
        return time.time() - loaded_at > self.config.cache_ttl

    @property
    def text_classifier(self) -> Any:
        """Get text classifier, loading it if necessary."""
        with self._text_lock:
            if self._text_classifier is None and not self._text_failed:
                self._load_text_model()
            elif self._text_classifier is not None and self._is_expired(self._text_loaded_at):
                self._load_text_model()
        return self._text_classifier

    @property
    def image_classifier(self) -> Optional[Any]:
        """Get image classifier, loading it if necessary."""
        with self._image_lock:
            if self._image_classifier is None and not self._image_failed:
                self._load_image_model()
            elif self._image_classifier is not None and self._is_expired(self._image_loaded_at):
                self._load_image_model()
        return self._image_classifier

    @property
    def audio_classifier(self) -> Optional[Any]:
        """Get audio classifier, loading it if necessary."""
        with self._audio_lock:
            if self._audio_classifier is None and not self._audio_failed:
                self._load_audio_model()
            elif self._audio_classifier is not None and self._is_expired(self._audio_loaded_at):
                self._load_audio_model()
        return self._audio_classifier

    def _load_text_model(self) -> None:
        """Load text classification model."""
        logger.info(f"Loading text model: {self.config.text_model}")
        start_time = time.time()

        try:
            from transformers import pipeline
            self._text_classifier = pipeline(
                "text-classification",
                model=self.config.text_model,
                device=self._device
            )
            # Set model to eval mode for deterministic inference
            if hasattr(self._text_classifier, 'model'):
                self._text_classifier.model.eval()
            self._text_loaded_at = time.time()
            duration = time.time() - start_time
            logger.info(f"Text model loaded successfully - Model: {self.config.text_model}, Duration: {round(duration * 1000, 2)}ms")
        except Exception as e:
            logger.warning(
                f"Failed to load primary text model, using fallback: {e} (fallback={self.config.text_fallback_model})"
            )
            try:
                from transformers import pipeline
                self._text_classifier = pipeline(
                    "sentiment-analysis",
                    device=self._device
                )
                if hasattr(self._text_classifier, 'model'):
                    self._text_classifier.model.eval()
                self._text_loaded_at = time.time()
                logger.info("Fallback text model loaded")
            except Exception as fallback_error:
                self._text_failed = True
                logger.error(f"Failed to load fallback text model - Error: {str(fallback_error)}")
                raise ModelError(
                    "Failed to load text model",
                    model_name=self.config.text_model,
                    details={'original_error': str(e), 'fallback_error': str(fallback_error)}
                )

    def _load_image_model(self) -> None:
        """Load image classification model."""
        logger.info(f"Loading image model: {self.config.image_model}")
        start_time = time.time()

        try:
            from transformers import pipeline
            self._image_classifier = pipeline(
                "image-classification",
                model=self.config.image_model,
                device=self._device
            )
            if hasattr(self._image_classifier, 'model'):
                self._image_classifier.model.eval()
            self._image_loaded_at = time.time()
            duration = time.time() - start_time
            logger.info(f"Image model loaded successfully - Model: {self.config.image_model}, Duration: {round(duration * 1000, 2)}ms")
        except Exception as e:
            logger.warning(f"Failed to load image model, image analysis will be limited - Error: {str(e)}")
            self._image_classifier = None
            self._image_failed = True

    def _load_audio_model(self) -> None:
        """Load audio classification model."""
        logger.info(f"Loading audio model: {self.config.audio_model}")
        start_time = time.time()

        try:
            from transformers import pipeline
            self._audio_classifier = pipeline(
                "audio-classification",
                model=self.config.audio_model,
                device=self._device
            )
            if hasattr(self._audio_classifier, 'model'):
                self._audio_classifier.model.eval()
            self._audio_loaded_at = time.time()
            duration = time.time() - start_time
            logger.info(f"Audio model loaded successfully - Model: {self.config.audio_model}, Duration: {round(duration * 1000, 2)}ms")
        except Exception as e:
            logger.warning(f"Failed to load audio model, audio analysis will be limited - Error: {str(e)}")
            self._audio_classifier = None
            self._audio_failed = True

    @property
    def videomae_model(self) -> Optional[Any]:
        """Get VideoMAE model (processor, model tuple), loading if necessary."""
        if not self.config.use_enhanced_models:
            return None
        with self._videomae_lock:
            if self._videomae_model is None:
                self._load_videomae_model()
        return self._videomae_model

    @property
    def emotion_classifier(self) -> Optional[Any]:
        """Get emotion classifier, loading if necessary."""
        if not self.config.use_enhanced_models:
            return None
        with self._emotion_lock:
            if self._emotion_classifier is None:
                self._load_emotion_model()
        return self._emotion_classifier

    @property
    def offensive_classifier(self) -> Optional[Any]:
        """Get offensive text classifier, loading if necessary."""
        if not self.config.use_enhanced_models:
            return None
        with self._offensive_lock:
            if self._offensive_classifier is None:
                self._load_offensive_model()
        return self._offensive_classifier

    @property
    def zero_shot_classifier(self) -> Optional[Any]:
        """Get zero-shot classifier, loading if necessary."""
        if not self.config.use_enhanced_models:
            return None
        with self._zero_shot_lock:
            if self._zero_shot_classifier is None:
                self._load_zero_shot_model()
        return self._zero_shot_classifier

    def _load_videomae_model(self) -> None:
        """Load VideoMAE model for action recognition."""
        model_name = self.config.videomae_model
        logger.info(f"Loading VideoMAE model: {model_name}")
        try:
            from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor
            processor = VideoMAEImageProcessor.from_pretrained(model_name)
            model = VideoMAEForVideoClassification.from_pretrained(model_name)
            model.eval()
            self._videomae_model = (processor, model)
            logger.info("VideoMAE model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load VideoMAE model: {e}")
            self._videomae_model = None

    def _load_emotion_model(self) -> None:
        """Load emotion classification model."""
        model_name = self.config.emotion_model
        logger.info(f"Loading emotion model: {model_name}")
        try:
            from transformers import pipeline
            self._emotion_classifier = pipeline(
                "audio-classification", model=model_name, device=self._device
            )
            if hasattr(self._emotion_classifier, 'model'):
                self._emotion_classifier.model.eval()
            logger.info("Emotion model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load emotion model: {e}")
            self._emotion_classifier = None

    def _load_offensive_model(self) -> None:
        """Load offensive text classification model."""
        model_name = self.config.offensive_model
        logger.info(f"Loading offensive model: {model_name}")
        try:
            from transformers import pipeline
            self._offensive_classifier = pipeline(
                "text-classification", model=model_name, device=self._device
            )
            if hasattr(self._offensive_classifier, 'model'):
                self._offensive_classifier.model.eval()
            logger.info("Offensive model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load offensive model: {e}")
            self._offensive_classifier = None

    def _load_zero_shot_model(self) -> None:
        """Load zero-shot classification model."""
        model_name = self.config.context_model
        logger.info(f"Loading zero-shot model: {model_name}")
        try:
            from transformers import pipeline
            self._zero_shot_classifier = pipeline(
                "zero-shot-classification", model=model_name, device=self._device
            )
            if hasattr(self._zero_shot_classifier, 'model'):
                self._zero_shot_classifier.model.eval()
            logger.info("Zero-shot model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load zero-shot model: {e}")
            self._zero_shot_classifier = None

    def load_all_models(self) -> None:
        """Load all models (used when lazy loading is disabled)."""
        logger.info("Loading all models...")
        start_time = time.time()

        # Load models sequentially to avoid memory issues
        _ = self.text_classifier
        _ = self.image_classifier
        _ = self.audio_classifier

        duration = time.time() - start_time
        logger.info(
            f"All models loaded - duration={round(duration * 1000, 2)}ms, "
            f"text={self._text_classifier is not None}, "
            f"image={self._image_classifier is not None}, "
            f"audio={self._audio_classifier is not None}"
        )

    def warm_up(self) -> None:
        """
        Run dummy input through each loaded model to warm up JIT/caches.
        Call after loading models to ensure first real prediction is fast.
        """
        logger.info("Warming up models...")

        import torch
        from PIL import Image

        with torch.no_grad():
            # Warm up text classifier
            if self._text_classifier is not None:
                try:
                    self._text_classifier("")
                    logger.info("Text model warmed up")
                except Exception as e:
                    logger.warning(f"Text model warm-up failed: {e}")

            # Warm up image classifier
            if self._image_classifier is not None:
                try:
                    dummy_image = Image.new('RGB', (224, 224), color=0)
                    self._image_classifier(dummy_image)
                    logger.info("Image model warmed up")
                except Exception as e:
                    logger.warning(f"Image model warm-up failed: {e}")

            # Warm up audio classifier
            if self._audio_classifier is not None:
                try:
                    import numpy as np
                    dummy_audio = np.zeros(16000, dtype=np.float32)
                    self._audio_classifier(dummy_audio, sampling_rate=16000)
                    logger.info("Audio model warmed up")
                except Exception as e:
                    logger.warning(f"Audio model warm-up failed: {e}")

        logger.info("Model warm-up complete")

    def unload_all_models(self) -> None:
        """Unload all models to free memory."""
        logger.info("Unloading all models...")

        with self._text_lock:
            self._text_classifier = None
            self._text_loaded_at = None

        with self._image_lock:
            self._image_classifier = None
            self._image_loaded_at = None

        with self._audio_lock:
            self._audio_classifier = None
            self._audio_loaded_at = None

        # Force garbage collection and clear caches
        from ..utils.performance import MemoryManager
        MemoryManager.clear_cache()

        logger.info("All models unloaded")

    def status(self) -> dict:
        """Get current model status."""
        return {
            'text_classifier': {
                'loaded': self._text_classifier is not None,
                'loaded_at': self._text_loaded_at,
            },
            'image_classifier': {
                'loaded': self._image_classifier is not None,
                'loaded_at': self._image_loaded_at,
            },
            'audio_classifier': {
                'loaded': self._audio_classifier is not None,
                'loaded_at': self._audio_loaded_at,
            },
            'device': 'cuda' if self._device == 0 else 'cpu',
            'lazy_load': self.config.lazy_load,
            'cache_ttl': self.config.cache_ttl,
        }


# Global instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get the global ModelManager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
