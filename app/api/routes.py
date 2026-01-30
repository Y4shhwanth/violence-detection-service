"""
Flask API routes for Violence Detection System.
Includes secure endpoints with validation, rate limiting, and proper error handling.
"""
import os
import uuid
import atexit
import glob
from typing import Dict, Any

from flask import Blueprint, request, jsonify, render_template, current_app, g
from werkzeug.utils import secure_filename

from .validators import (
    FileValidator,
    validate_api_key,
    rate_limit,
    add_rate_limit_headers,
    validate_text_input,
)
from ..analysis import MultiModalFusion, TextAnalyzer, VideoAnalyzer
from ..utils.errors import (
    ViolenceDetectionError,
    ValidationError,
    FileValidationError,
)
from ..utils.logging import get_logger
from ..utils.cache import get_cache, compute_file_hash
from ..config import get_config

logger = get_logger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize components
file_validator = FileValidator()
fusion = MultiModalFusion()


@api_bp.after_request
def after_request(response):
    """Add security and rate limit headers to all responses."""
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Rate limit headers
    response = add_rate_limit_headers(response)

    return response


@api_bp.errorhandler(ViolenceDetectionError)
def handle_violence_detection_error(error: ViolenceDetectionError):
    """Handle custom exceptions with secure error messages."""
    # Log detailed error server-side
    logger.error(
        f"Error {error.error_id}: {error.message}",
        extra=error.to_log_dict()
    )

    # Return generic error to client (no stack traces)
    return jsonify(error.to_dict()), 400


@api_bp.errorhandler(Exception)
def handle_generic_error(error: Exception):
    """Handle unexpected errors securely."""
    error_id = str(uuid.uuid4())[:8]

    # Log full error server-side
    logger.exception(f"Unexpected error {error_id}: {error}")

    # Return generic message to client
    return jsonify({
        'success': False,
        'error': 'InternalError',
        'message': 'An unexpected error occurred',
        'error_id': error_id,
    }), 500


@api_bp.route('/')
def index():
    """Render main UI."""
    return render_template('react_style.html')


@api_bp.route('/old')
def old_index():
    """Render legacy UI."""
    return render_template('index.html')


@api_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    from ..models.loader import get_model_manager

    manager = get_model_manager()
    status = manager.status()

    return jsonify({
        'status': 'healthy',
        'models': status,
        'cache': get_cache().stats(),
    })


@api_bp.route('/predict', methods=['POST'])
@validate_api_key
@rate_limit
def predict():
    """
    Main prediction endpoint for multimodal analysis.
    Supports video + text input with parallel processing.
    """
    config = get_config()
    video_path = None

    try:
        results = {
            'success': False,
            'video_prediction': None,
            'audio_prediction': None,
            'text_prediction': None,
            'fused_prediction': None,
            'message': ''
        }

        # Process video file
        video_file = request.files.get('video')
        if video_file and video_file.filename:
            # Validate file
            file_validator.validate(video_file)

            filename = secure_filename(video_file.filename)
            video_path = os.path.join(config.file.upload_folder, filename)
            video_file.save(video_path)

            # Check cache
            if config.cache.enabled:
                file_hash = compute_file_hash(video_path)
                cache = get_cache()

                cached_video = cache.get_by_hash(file_hash, 'video')
                cached_audio = cache.get_by_hash(file_hash, 'audio')

                if cached_video and cached_audio:
                    logger.info(f"Cache hit for video: {filename}")
                    results['video_prediction'] = cached_video
                    results['audio_prediction'] = cached_audio
                else:
                    # Analyze and cache
                    results['video_prediction'] = fusion.analyze_video_only(video_path)
                    results['audio_prediction'] = fusion.analyze_audio_only(video_path)

                    cache.set_by_hash(file_hash, 'video', results['video_prediction'])
                    cache.set_by_hash(file_hash, 'audio', results['audio_prediction'])
            else:
                results['video_prediction'] = fusion.analyze_video_only(video_path)
                results['audio_prediction'] = fusion.analyze_audio_only(video_path)

        # Process text
        text_input = request.form.get('text', '')
        if text_input:
            text_input = validate_text_input(text_input)

            # Check cache for text
            if config.cache.enabled:
                text_bytes = text_input.encode('utf-8')
                cache = get_cache()
                cached_text = cache.get(text_bytes, 'text')

                if cached_text:
                    logger.info("Cache hit for text")
                    results['text_prediction'] = cached_text
                else:
                    results['text_prediction'] = fusion.analyze_text_only(text_input)
                    cache.set(text_bytes, 'text', results['text_prediction'])
            else:
                results['text_prediction'] = fusion.analyze_text_only(text_input)

        # Create fused prediction
        predictions = [
            results['video_prediction'],
            results['audio_prediction'],
            results['text_prediction']
        ]
        valid_predictions = [p for p in predictions if p and p.get('class') != 'Error']

        if valid_predictions:
            results['fused_prediction'] = fusion._fuse_predictions(valid_predictions)

        results['success'] = True
        results['message'] = 'Analysis completed using pretrained models'

        return jsonify(results)

    finally:
        # Cleanup uploaded file
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError as e:
                logger.warning(f"Failed to cleanup file: {e}")


@api_bp.route('/predict_text', methods=['POST'])
@validate_api_key
@rate_limit
def predict_text():
    """Text-only prediction endpoint with detailed reasoning."""
    data = request.get_json()
    text = data.get('text', '') if data else ''

    text = validate_text_input(text)
    config = get_config()

    # Check cache
    if config.cache.enabled:
        text_bytes = text.encode('utf-8')
        cache = get_cache()
        cached = cache.get(text_bytes, 'text')

        if cached:
            logger.info("Cache hit for text prediction")
            result = cached
        else:
            result = fusion.analyze_text_only(text)
            cache.set(text_bytes, 'text', result)
    else:
        result = fusion.analyze_text_only(text)

    response = {
        'success': True,
        'prediction': result['class'],
        'confidence': result['confidence']
    }

    # Add optional fields
    for field in ['reasoning', 'keywords_found', 'ml_score']:
        if field in result:
            response[field] = result[field]

    return jsonify(response)


@api_bp.route('/predict_video', methods=['POST'])
@validate_api_key
@rate_limit
def predict_video():
    """Video-only prediction endpoint with detailed reasoning."""
    if 'video' not in request.files:
        raise ValidationError("No video provided", field='video')

    video_file = request.files['video']
    file_validator.validate(video_file)

    config = get_config()
    filename = secure_filename(video_file.filename)
    video_path = os.path.join(config.file.upload_folder, filename)

    try:
        video_file.save(video_path)

        # Check cache
        if config.cache.enabled:
            file_hash = compute_file_hash(video_path)
            cache = get_cache()
            cached = cache.get_by_hash(file_hash, 'video')

            if cached:
                logger.info("Cache hit for video prediction")
                result = cached
            else:
                result = fusion.analyze_video_only(video_path)
                cache.set_by_hash(file_hash, 'video', result)
        else:
            result = fusion.analyze_video_only(video_path)

        response = {
            'success': True,
            'prediction': result['class'],
            'confidence': result['confidence'],
            'video_path': filename
        }

        # Add optional fields
        for field in ['reasoning', 'violent_frames', 'avg_score', 'max_score', 'total_frames_analyzed']:
            if field in result:
                response[field] = result[field]

        return jsonify(response)

    finally:
        # Cleanup
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError as e:
                logger.warning(f"Failed to cleanup file: {e}")


def cleanup_uploads():
    """Cleanup any leftover upload files on shutdown."""
    config = get_config()
    upload_folder = config.file.upload_folder

    if os.path.exists(upload_folder):
        for file_path in glob.glob(os.path.join(upload_folder, '*')):
            if os.path.isfile(file_path) and not file_path.endswith('.gitkeep'):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to cleanup {file_path}: {e}")


# Register cleanup on shutdown
atexit.register(cleanup_uploads)
