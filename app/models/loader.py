"""
Lazy model loading and management for Violence Detection System.
Models are loaded on first use and cached, eliminating startup time.
"""
import time
from typing import Optional, Any
from threading import Lock

import torch
from transformers import pipeline

from ..config import get_config
from ..utils.logging import get_logger
from ..utils.errors import ModelError

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
        self._device = 0 if torch.cuda.is_available() else -1

        # Model storage
        self._text_classifier = None
        self._image_classifier = None
        self._audio_classifier = None

        # Loading timestamps for TTL
        self._text_loaded_at: Optional[float] = None
        self._image_loaded_at: Optional[float] = None
        self._audio_loaded_at: Optional[float] = None

        # Individual locks for thread-safe lazy loading
        self._text_lock = Lock()
        self._image_lock = Lock()
        self._audio_lock = Lock()

        self._initialized = True

        logger.info(
            "ModelManager initialized",
            device='cuda' if self._device == 0 else 'cpu',
            lazy_load=self.config.lazy_load
        )

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
            if self._text_classifier is None or self._is_expired(self._text_loaded_at):
                self._load_text_model()
        return self._text_classifier

    @property
    def image_classifier(self) -> Optional[Any]:
        """Get image classifier, loading it if necessary."""
        with self._image_lock:
            if self._image_classifier is None or self._is_expired(self._image_loaded_at):
                self._load_image_model()
        return self._image_classifier

    @property
    def audio_classifier(self) -> Optional[Any]:
        """Get audio classifier, loading it if necessary."""
        with self._audio_lock:
            if self._audio_classifier is None or self._is_expired(self._audio_loaded_at):
                self._load_audio_model()
        return self._audio_classifier

    def _load_text_model(self) -> None:
        """Load text classification model."""
        logger.info(f"Loading text model: {self.config.text_model}")
        start_time = time.time()

        try:
            self._text_classifier = pipeline(
                "text-classification",
                model=self.config.text_model,
                device=self._device
            )
            self._text_loaded_at = time.time()
            duration = time.time() - start_time
            logger.info(
                "Text model loaded successfully",
                model=self.config.text_model,
                duration_ms=round(duration * 1000, 2)
            )
        except Exception as e:
            logger.warning(
                f"Failed to load primary text model, using fallback",
                error=str(e),
                fallback=self.config.text_fallback_model
            )
            try:
                self._text_classifier = pipeline(
                    "sentiment-analysis",
                    device=self._device
                )
                self._text_loaded_at = time.time()
                logger.info("Fallback text model loaded")
            except Exception as fallback_error:
                logger.error(
                    "Failed to load fallback text model",
                    error=str(fallback_error)
                )
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
            self._image_classifier = pipeline(
                "image-classification",
                model=self.config.image_model,
                device=self._device
            )
            self._image_loaded_at = time.time()
            duration = time.time() - start_time
            logger.info(
                "Image model loaded successfully",
                model=self.config.image_model,
                duration_ms=round(duration * 1000, 2)
            )
        except Exception as e:
            logger.warning(
                "Failed to load image model, image analysis will be limited",
                error=str(e)
            )
            self._image_classifier = None

    def _load_audio_model(self) -> None:
        """Load audio classification model."""
        logger.info(f"Loading audio model: {self.config.audio_model}")
        start_time = time.time()

        try:
            self._audio_classifier = pipeline(
                "audio-classification",
                model=self.config.audio_model,
                device=self._device
            )
            self._audio_loaded_at = time.time()
            duration = time.time() - start_time
            logger.info(
                "Audio model loaded successfully",
                model=self.config.audio_model,
                duration_ms=round(duration * 1000, 2)
            )
        except Exception as e:
            logger.warning(
                "Failed to load audio model, audio analysis will be limited",
                error=str(e)
            )
            self._audio_classifier = None

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
            "All models loaded",
            duration_ms=round(duration * 1000, 2),
            text_loaded=self._text_classifier is not None,
            image_loaded=self._image_classifier is not None,
            audio_loaded=self._audio_classifier is not None
        )

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

        # Force garbage collection
        import gc
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

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
