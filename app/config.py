"""
Configuration management for Violence Detection System.
All thresholds, settings, and environment variables are externalized here.
"""
import os
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TextAnalysisConfig:
    """Configuration for text analysis thresholds."""
    keyword_threshold: int = 15
    extreme_keyword_score: int = 35
    physical_keyword_score: int = 25
    weapons_threats_score: int = 20
    other_keyword_score: int = 15
    threat_pattern_score: int = 40
    ml_toxic_threshold: float = 50.0
    ml_negative_threshold: float = 60.0
    confidence_boost: float = 20.0
    min_confidence: float = 60.0
    max_confidence: float = 95.0


@dataclass
class VideoAnalysisConfig:
    """Configuration for video analysis thresholds."""
    frame_sample_count: int = 15
    combined_threshold: int = 20
    max_heuristic_threshold: int = 35
    avg_heuristic_threshold: int = 25
    ml_threshold: int = 40
    frame_violence_threshold: int = 30

    # Violence detection thresholds
    violence_threshold: int = 60      # combined_score threshold for is_violent
    ml_min_score: int = 20            # minimum ML score to count as signal

    # Heuristic thresholds
    red_intensity_high: int = 130
    red_dominance_high: float = 0.25
    red_intensity_medium: int = 110
    red_dominance_medium: float = 0.15
    red_intensity_low: int = 100

    brightness_very_dark: int = 90
    brightness_moderately_dark: int = 110

    color_variance_high: int = 60
    color_variance_medium: int = 50

    edge_density_high: float = 0.12
    edge_density_medium: float = 0.08

    motion_blur_threshold: int = 100


@dataclass
class AudioAnalysisConfig:
    """Configuration for audio analysis thresholds."""
    violence_threshold: int = 30
    audio_duration_seconds: int = 30
    sample_rate: int = 16000
    loudness_spike_threshold: int = 10
    zcr_threshold: float = 0.15
    confidence_boost: float = 20.0
    min_confidence: float = 60.0
    max_confidence: float = 95.0

    # Sound weights
    sound_weights: Dict[str, int] = field(default_factory=lambda: {
        'gunshot': 60, 'gun': 60, 'explosion': 60, 'bomb': 60,
        'scream': 50, 'screaming': 50, 'shout': 45, 'yell': 45,
        'siren': 40, 'alarm': 40, 'police': 40, 'fire': 35,
        'crash': 35, 'smash': 35, 'breaking': 35, 'glass': 30,
        'fight': 40, 'punch': 40, 'hit': 35, 'bang': 35,
        'emergency': 35, 'distress': 40, 'panic': 40
    })


@dataclass
class SecurityConfig:
    """Security-related configuration."""
    secret_key: str = field(default_factory=lambda: os.getenv(
        'SECRET_KEY',
        secrets.token_hex(32)
    ))
    debug: bool = field(default_factory=lambda: os.getenv(
        'FLASK_DEBUG', 'False'
    ).lower() == 'true')

    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: [
        origin.strip()
        for origin in os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5001,http://localhost:5173,https://frontend-nine-phi-91.vercel.app').split(',')
        if origin.strip()
    ])
    cors_allow_all: bool = field(default_factory=lambda: os.getenv(
        'CORS_ALLOW_ALL', 'False'
    ).lower() == 'true')

    # Rate limiting
    rate_limit_requests: int = field(default_factory=lambda: int(
        os.getenv('RATE_LIMIT_REQUESTS', '10')
    ))
    rate_limit_window: int = field(default_factory=lambda: int(
        os.getenv('RATE_LIMIT_WINDOW', '60')
    ))  # seconds

    # API authentication
    api_key_enabled: bool = field(default_factory=lambda: os.getenv(
        'API_KEY_ENABLED', 'False'
    ).lower() == 'true')
    api_keys: List[str] = field(default_factory=lambda: [
        key.strip()
        for key in os.getenv('API_KEYS', '').split(',')
        if key.strip()
    ])


@dataclass
class FileConfig:
    """File upload and validation configuration."""
    max_content_length: int = field(default_factory=lambda: int(
        os.getenv('MAX_CONTENT_LENGTH', str(50 * 1024 * 1024))
    ))  # 50MB default (reduced from 100MB)
    upload_folder: str = field(default_factory=lambda: os.getenv(
        'UPLOAD_FOLDER', 'static/uploads'
    ))

    # Allowed file extensions
    allowed_video_extensions: set = field(default_factory=lambda: {
        'mp4', 'avi', 'mov', 'mkv', 'webm'
    })

    # Allowed MIME types
    allowed_video_mimetypes: set = field(default_factory=lambda: {
        'video/mp4', 'video/avi', 'video/quicktime',
        'video/x-matroska', 'video/webm', 'video/x-msvideo'
    })

    # Magic bytes for video formats
    video_magic_bytes: Dict[str, bytes] = field(default_factory=lambda: {
        'mp4': b'\x00\x00\x00',  # ftyp box (check for 'ftyp' at offset 4)
        'avi': b'RIFF',
        'mkv': b'\x1a\x45\xdf\xa3',
        'webm': b'\x1a\x45\xdf\xa3',
        'mov': b'\x00\x00\x00',  # Similar to mp4
    })


@dataclass
class CacheConfig:
    """Caching configuration."""
    enabled: bool = field(default_factory=lambda: os.getenv(
        'CACHE_ENABLED', 'True'
    ).lower() == 'true')
    ttl_seconds: int = field(default_factory=lambda: int(
        os.getenv('CACHE_TTL', '3600')
    ))  # 1 hour default
    max_size: int = field(default_factory=lambda: int(
        os.getenv('CACHE_MAX_SIZE', '100')
    ))


@dataclass
class ModelConfig:
    """Model loading configuration."""
    text_model: str = field(default_factory=lambda: os.getenv(
        'TEXT_MODEL', 'unitary/toxic-bert'
    ))
    text_fallback_model: str = 'sentiment-analysis'

    image_model: str = field(default_factory=lambda: os.getenv(
        'IMAGE_MODEL', 'Falconsai/nsfw_image_detection'
    ))

    audio_model: str = field(default_factory=lambda: os.getenv(
        'AUDIO_MODEL', 'MIT/ast-finetuned-audioset-10-10-0.4593'
    ))

    # Skip ML model loading entirely (for low-memory hosts like Render free tier)
    skip_ml_models: bool = field(default_factory=lambda: os.getenv(
        'SKIP_ML_MODELS', 'False'
    ).lower() == 'true')

    # Lazy loading
    lazy_load: bool = field(default_factory=lambda: os.getenv(
        'LAZY_LOAD_MODELS', 'True'
    ).lower() == 'true')

    # Model cache TTL (seconds) - 0 means no expiry
    cache_ttl: int = field(default_factory=lambda: int(
        os.getenv('MODEL_CACHE_TTL', '0')
    ))

    # Enhanced models (Phase 2)
    use_enhanced_models: bool = field(default_factory=lambda: os.getenv(
        'USE_ENHANCED_MODELS', 'False'
    ).lower() == 'true')
    videomae_model: str = field(default_factory=lambda: os.getenv(
        'VIDEOMAE_MODEL', 'MCG-NJU/videomae-base-finetuned-kinetics'
    ))
    emotion_model: str = field(default_factory=lambda: os.getenv(
        'EMOTION_MODEL', 'ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition'
    ))
    offensive_model: str = field(default_factory=lambda: os.getenv(
        'OFFENSIVE_MODEL', 'cardiffnlp/twitter-roberta-base-offensive'
    ))
    context_model: str = field(default_factory=lambda: os.getenv(
        'CONTEXT_MODEL', 'facebook/bart-large-mnli'
    ))


@dataclass
class FusionConfig:
    """Configuration for weighted fusion."""
    video_weight: float = 0.4
    audio_weight: float = 0.3
    text_weight: float = 0.3
    cross_modal_boost: float = 8.0
    cross_modal_penalty: float = 10.0
    embedding_similarity_threshold: float = 0.65
    min_modalities_for_violence: int = 2
    single_modality_threshold: float = 90.0


@dataclass
class DatabaseConfig:
    """Database configuration."""
    db_url: Optional[str] = field(default_factory=lambda: os.getenv(
        'DATABASE_URL', None
    ))  # None = auto SQLite


@dataclass
class JobQueueConfig:
    """Job queue configuration."""
    redis_url: Optional[str] = field(default_factory=lambda: os.getenv(
        'REDIS_URL', None
    ))
    max_workers: int = field(default_factory=lambda: int(
        os.getenv('JOB_MAX_WORKERS', '2')
    ))
    job_ttl: int = field(default_factory=lambda: int(
        os.getenv('JOB_TTL', '3600')
    ))


@dataclass
class RAGConfig:
    """RAG Policy Engine configuration."""
    embedding_model: str = field(default_factory=lambda: os.getenv(
        'RAG_EMBEDDING_MODEL', 'all-MiniLM-L6-v2'
    ))
    index_path: str = field(default_factory=lambda: os.getenv(
        'RAG_INDEX_PATH', 'data/faiss_index'
    ))
    use_rag: bool = field(default_factory=lambda: os.getenv(
        'USE_RAG_POLICY', 'False'
    ).lower() == 'true')


@dataclass
class LiveDetectionConfig:
    """Live detection / real-time monitoring configuration."""
    frame_skip: int = field(default_factory=lambda: int(
        os.getenv('LIVE_FRAME_SKIP', '5')
    ))  # Analyze every Nth frame
    alert_threshold: float = field(default_factory=lambda: float(
        os.getenv('LIVE_ALERT_THRESHOLD', '70.0')
    ))  # Confidence threshold for alerts
    max_fps: int = field(default_factory=lambda: int(
        os.getenv('LIVE_MAX_FPS', '30')
    ))
    frame_width: int = 640
    frame_height: int = 480


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = field(default_factory=lambda: os.getenv(
        'LOG_LEVEL', 'INFO'
    ))
    format: str = field(default_factory=lambda: os.getenv(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_path: Optional[str] = field(default_factory=lambda: os.getenv(
        'LOG_FILE', None
    ))
    max_bytes: int = field(default_factory=lambda: int(
        os.getenv('LOG_MAX_BYTES', str(10 * 1024 * 1024))
    ))  # 10MB
    backup_count: int = field(default_factory=lambda: int(
        os.getenv('LOG_BACKUP_COUNT', '5')
    ))


@dataclass
class Config:
    """Main configuration class combining all settings."""
    text: TextAnalysisConfig = field(default_factory=TextAnalysisConfig)
    video: VideoAnalysisConfig = field(default_factory=VideoAnalysisConfig)
    audio: AudioAnalysisConfig = field(default_factory=AudioAnalysisConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    file: FileConfig = field(default_factory=FileConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    fusion: FusionConfig = field(default_factory=FusionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    job_queue: JobQueueConfig = field(default_factory=JobQueueConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    live_detection: LiveDetectionConfig = field(default_factory=LiveDetectionConfig)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment variables."""
    global _config
    _config = Config()
    return _config
