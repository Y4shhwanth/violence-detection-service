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
from ..database.session import get_db_session
from ..database.models import AnalysisResult, ModerationStats

logger = get_logger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize components
file_validator = FileValidator()
_fusion = None


def _get_fusion():
    """Lazily initialize MultiModalFusion to avoid heavy imports at startup."""
    global _fusion
    if _fusion is None:
        _fusion = MultiModalFusion()
    return _fusion


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
    """Render AI-powered animated UI."""
    return render_template('ai_ui.html')


@api_bp.route('/classic')
def classic_ui():
    """Render classic UI."""
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


def _store_predict_result(results, video_path, text_input):
    """Store a /predict result in the database (mirrors AnalysisService._store_result)."""
    import datetime

    job_id = str(uuid.uuid4())
    results['job_id'] = job_id

    with get_db_session() as session:
        record = AnalysisResult(
            id=str(uuid.uuid4()),
            job_id=job_id,
            has_video=video_path is not None,
            has_text=bool(text_input),
            video_filename=os.path.basename(video_path) if video_path else None,
            text_length=len(text_input) if text_input else 0,
            final_decision=results.get('final_decision', 'Unknown'),
            confidence=results.get('confidence', 0),
            decision_tier=(results.get('fused_prediction') or {}).get('decision_tier'),
            video_confidence=(results.get('video_prediction') or {}).get('confidence'),
            audio_confidence=(results.get('audio_prediction') or {}).get('confidence'),
            text_confidence=(results.get('text_prediction') or {}).get('confidence'),
            severity_score=(results.get('severity') or {}).get('severity_score'),
            severity_label=(results.get('severity') or {}).get('severity_label'),
            result_json=results,
            processing_time_ms=results.get('processing_time_ms'),
        )
        session.add(record)

        today = datetime.date.today().isoformat()
        stats = session.query(ModerationStats).filter_by(date=today).first()
        if not stats:
            stats = ModerationStats(date=today)
            session.add(stats)

        stats.total_analyses += 1
        decision = results.get('final_decision', '')
        if decision == 'Violation':
            stats.violations += 1
        elif decision == 'Review Required':
            stats.reviews += 1
        else:
            stats.verified += 1

        n = stats.total_analyses
        stats.avg_confidence = (
            (stats.avg_confidence * (n - 1) + results.get('confidence', 0)) / n
        )
        processing_time_ms = results.get('processing_time_ms', 0)
        stats.avg_processing_time_ms = (
            (stats.avg_processing_time_ms * (n - 1) + processing_time_ms) / n
        )


@api_bp.route('/predict', methods=['POST'])
@validate_api_key
@rate_limit
def predict():
    """
    Main prediction endpoint for multimodal analysis.
    Supports video + text input with parallel processing.
    """
    import time as _time
    config = get_config()
    video_path = None
    text_input = ''
    _start_time = _time.time()

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
                    # Use temporal analysis for violation detection
                    fusion = _get_fusion()
                    results['video_prediction'] = fusion._safe_analyze_temporal(
                        fusion.video_analyzer, video_path, 'video'
                    )
                    results['audio_prediction'] = fusion._safe_analyze_temporal(
                        fusion.audio_analyzer, video_path, 'audio'
                    )

                    cache.set_by_hash(file_hash, 'video', results['video_prediction'])
                    cache.set_by_hash(file_hash, 'audio', results['audio_prediction'])
            else:
                fusion = _get_fusion()
                results['video_prediction'] = fusion._safe_analyze_temporal(
                    fusion.video_analyzer, video_path, 'video'
                )
                results['audio_prediction'] = fusion._safe_analyze_temporal(
                    fusion.audio_analyzer, video_path, 'audio'
                )

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
                    fusion = _get_fusion()
                    results['text_prediction'] = fusion._safe_analyze_temporal(
                        fusion.text_analyzer, text_input, 'text'
                    )
                    cache.set(text_bytes, 'text', results['text_prediction'])
            else:
                fusion = _get_fusion()
                results['text_prediction'] = fusion._safe_analyze_temporal(
                    fusion.text_analyzer, text_input, 'text'
                )

        # Create fused prediction
        predictions = [
            results['video_prediction'],
            results['audio_prediction'],
            results['text_prediction']
        ]
        valid_predictions = [p for p in predictions if p and p.get('class') != 'Error']

        if valid_predictions:
            results['fused_prediction'] = _get_fusion()._fuse_predictions(valid_predictions)

        # Merge violations from temporal analysis
        all_violations = []
        for key in ['video_prediction', 'audio_prediction', 'text_prediction']:
            pred = results.get(key)
            if pred and 'violations' in pred:
                all_violations.extend(pred['violations'])
        all_violations.sort(key=lambda v: v.get('start_seconds', v.get('sentence_index', 0)))
        results['violations'] = all_violations

        # --- Enhanced pipeline: severity, embeddings, policy, LLM ---
        try:
            results = _get_fusion().enhance_results(
                results,
                text_input=text_input if text_input else None,
                audio_data=None,
                video_frames=None,
            )
        except Exception as e:
            logger.warning(f"Enhancement pipeline failed (non-fatal): {e}")

        results['success'] = True
        results['message'] = 'Analysis completed using pretrained models'

        # Build unified response format with 3-tier decision
        fused = results.get('fused_prediction') or {}
        fused_class = fused.get('class', 'Non-Violence')
        confidence = fused.get('confidence', 0)

        # 3-tier decision: Violation / Review Required / Verified
        decision_tier = fused.get('decision_tier', None)
        if decision_tier:
            final_decision = decision_tier
        else:
            final_decision = 'Violation' if fused_class == 'Violence' else 'Verified'

        # Generate message from explanation
        explanation = results.get('structured_explanation', {})

        if final_decision == 'Violation':
            message = explanation.get('summary', 'Violent content detected.')
        elif final_decision == 'Review Required':
            message = 'Content flagged for manual review — moderate indicators detected.'
        else:
            message = explanation.get('summary', 'No significant violence indicators found.')

        # Recommended action per tier
        recommended_action = None
        if final_decision == 'Violation':
            if all_violations:
                video_v = [v for v in all_violations if v.get('modality') == 'video']
                if video_v:
                    segs = [f"{v['start_time']}-{v['end_time']}" for v in video_v]
                    recommended_action = f"Remove or blur segment(s) {', '.join(segs)}."
                else:
                    recommended_action = explanation.get('compliance_suggestion', 'Review content.')
            else:
                recommended_action = explanation.get('compliance_suggestion', 'Review content for policy compliance.')
        elif final_decision == 'Review Required':
            recommended_action = 'Manual review recommended before publishing.'

        results['final_decision'] = final_decision
        results['confidence'] = float(confidence)
        results['message'] = message
        if recommended_action:
            results['recommended_action'] = recommended_action

        # Processing time
        results['processing_time_ms'] = int((_time.time() - _start_time) * 1000)

        # Store result in database (non-fatal)
        try:
            _store_predict_result(results, video_path, text_input)
        except Exception as e:
            logger.warning(f"Failed to store predict result in DB: {e}")

        # Debug block: include intermediate scores when debug=true
        debug_flag = request.form.get('debug', request.args.get('debug', '')).lower()
        if debug_flag in ('true', '1', 'yes'):
            results['debug'] = {
                'decision_tier': final_decision,
                'decision_reason': fused.get('decision_reason', 'unknown'),
                'fusion_confidence': float(confidence),
                'calibrated_scores': fused.get('calibrated_scores', {}),
                'raw_scores': fused.get('raw_scores', {}),
                'modality_classes': {
                    'video': (results.get('video_prediction') or {}).get('class', 'N/A'),
                    'audio': (results.get('audio_prediction') or {}).get('class', 'N/A'),
                    'text': (results.get('text_prediction') or {}).get('class', 'N/A'),
                },
                'modality_confidences': {
                    'video': (results.get('video_prediction') or {}).get('confidence', 0),
                    'audio': (results.get('audio_prediction') or {}).get('confidence', 0),
                    'text': (results.get('text_prediction') or {}).get('confidence', 0),
                },
                'cross_modal_adjustment': fused.get('cross_modal_adjustment', 0),
                'severity': results.get('severity', {}),
                'embedding_adjustment': results.get('embedding_adjustment', {}),
                'false_positive_analysis': results.get('false_positive_analysis', {}),
            }

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
            result = _get_fusion().analyze_text_only(text)
            cache.set(text_bytes, 'text', result)
    else:
        result = _get_fusion().analyze_text_only(text)

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
                result = _get_fusion().analyze_video_only(video_path)
                cache.set_by_hash(file_hash, 'video', result)
        else:
            result = _get_fusion().analyze_video_only(video_path)

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


# ------------------------------------------------------------------
# Async analysis endpoints (Phase 1)
# ------------------------------------------------------------------

@api_bp.route('/analyze', methods=['POST'])
@validate_api_key
@rate_limit
def submit_analysis():
    """Submit async analysis job. Returns job_id for polling."""
    from ..services.job_queue import get_job_queue
    from ..services.analysis_service import get_analysis_service

    config = get_config()
    jq = get_job_queue()

    # Ensure workers are started and handler is set
    svc = get_analysis_service()
    if not jq._handler:
        jq.set_handler(svc.process_job)
        jq.start_workers()

    video_path = None
    text_input = request.form.get('text', '').strip() or None

    video_file = request.files.get('video')
    if video_file and video_file.filename:
        file_validator.validate(video_file)
        filename = f"{uuid.uuid4().hex}_{secure_filename(video_file.filename)}"
        video_path = os.path.join(config.file.upload_folder, filename)
        video_file.save(video_path)

    if not video_path and not text_input:
        return jsonify({'success': False, 'error': 'No input provided'}), 400

    job_id = jq.submit_job(video_path=video_path, text_input=text_input)
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


@api_bp.route('/status/<job_id>')
def job_status(job_id):
    """Poll job progress."""
    from ..services.job_queue import get_job_queue
    jq = get_job_queue()
    status = jq.get_status(job_id)
    if not status:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(status)


@api_bp.route('/result/<job_id>')
def job_result(job_id):
    """Fetch completed job result."""
    from ..services.job_queue import get_job_queue
    jq = get_job_queue()
    result = jq.get_result(job_id)
    if result is None:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(result)


@api_bp.route('/ask-analysis', methods=['POST'])
def ask_analysis():
    """
    AI Moderation Copilot endpoint.
    Accepts a natural language question about an analysis result
    and returns an evidence-backed answer with policy references.
    """
    data = request.get_json()
    if not data or not data.get('question'):
        return jsonify({
            'success': False,
            'error': 'Missing required field: question',
        }), 400

    try:
        from ..services.ai_copilot import get_ai_copilot
        copilot = get_ai_copilot()

        result = copilot.ask(
            question=data['question'],
            analysis_id=data.get('analysis_id'),
            analysis_data=data.get('analysis_data'),
        )

        return jsonify({'success': True, **result})

    except Exception as e:
        logger.error(f"AI Copilot error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


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
