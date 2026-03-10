"""
Violence Detection System Flask Application Factory.
Creates and configures the Flask application with all security features.
"""
import os
import json
from flask import Flask
from flask_cors import CORS

from .config import get_config
from .utils.logging import setup_logging, RequestLogger, get_logger
from .api.routes import api_bp
from .api.dashboard_routes import dashboard_bp

# SocketIO instance (initialized in create_app)
socketio = None


class NumpySafeEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types from ML model outputs."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.bool_):
                return bool(obj)
        except ImportError:
            pass
        return super().default(obj)


class NumpySafeProvider(Flask.json_provider_class):
    """Flask JSON provider that handles numpy types."""
    def dumps(self, obj, **kwargs):
        kwargs.setdefault('cls', NumpySafeEncoder)
        return super().dumps(obj, **kwargs)


def create_app(config_override: dict = None) -> Flask:
    """
    Application factory for creating Flask app instances.

    Args:
        config_override: Optional configuration overrides

    Returns:
        Configured Flask application
    """
    # Load configuration
    config = get_config()

    # Setup logging first
    setup_logging(
        level=config.logging.level,
        log_format=config.logging.format,
        file_path=config.logging.file_path,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count
    )

    logger = get_logger(__name__)
    logger.info("Creating Flask application...")

    # Create Flask app
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    # Use numpy-safe JSON provider to handle ML model output types
    app.json_provider_class = NumpySafeProvider
    app.json = NumpySafeProvider(app)

    # Apply configuration
    app.config['SECRET_KEY'] = config.security.secret_key
    app.config['MAX_CONTENT_LENGTH'] = config.file.max_content_length
    app.config['UPLOAD_FOLDER'] = config.file.upload_folder

    # Apply any overrides
    if config_override:
        app.config.update(config_override)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Configure CORS
    _configure_cors(app, config)

    # Initialize request logging
    RequestLogger(app)

    # Initialize database
    try:
        from .database.session import init_db
        init_db(config.database.db_url)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed (non-fatal): {e}")

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)

    # Initialize Flask-SocketIO for live detection
    _init_socketio(app)

    # Serve React frontend production build at /app
    _register_react_frontend(app)

    # Register error handlers at app level
    _register_error_handlers(app)

    cors_str = str(config.security.cors_origins if not config.security.cors_allow_all else ['*'])
    logger.info(f"Flask application created - Debug: {config.security.debug}, CORS: {cors_str}")

    return app


def _init_socketio(app: Flask) -> None:
    """Initialize Flask-SocketIO for real-time live detection."""
    global socketio
    logger = get_logger(__name__)

    try:
        from flask_socketio import SocketIO, emit

        socketio = SocketIO(
            app,
            cors_allowed_origins='*',
            async_mode='threading',
            logger=False,
            engineio_logger=False,
        )

        @socketio.on('start_live_detection')
        def handle_start_live(data):
            """Start a live detection session."""
            from .analysis.live_detector import get_live_detector
            detector = get_live_detector()
            source = data.get('source', 0)
            # For webcam source, use 0; for RTSP, pass URL string
            if source == 'webcam':
                source = 0
            session_id = detector.start_stream(
                source=source,
                emit_callback=emit,
            )
            emit('live_status', {
                'session_id': session_id,
                'status': 'started',
            })

        @socketio.on('stop_live_detection')
        def handle_stop_live(data):
            """Stop a live detection session."""
            from .analysis.live_detector import get_live_detector
            detector = get_live_detector()
            session_id = data.get('session_id', '')
            detector.stop_stream(session_id)
            emit('live_status', {
                'session_id': session_id,
                'status': 'stopped',
            })

        @socketio.on('analyze_frame')
        def handle_analyze_frame(data):
            """Analyze a single frame sent from the client."""
            import base64
            import numpy as np
            import cv2

            try:
                from .analysis.live_detector import get_live_detector
                detector = get_live_detector()

                # Decode base64 frame from client
                frame_data = data.get('frame', '')
                if ',' in frame_data:
                    frame_data = frame_data.split(',')[1]

                img_bytes = base64.b64decode(frame_data)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is not None:
                    result = detector.analyze_single_frame(frame)
                    import time
                    emit('detection_result', {
                        'session_id': 'webcam',
                        'timestamp': time.strftime('%H:%M:%S'),
                        'violence_detected': result.get('is_violent', False),
                        'confidence': round(result.get('confidence', 0), 1),
                        'violence_score': round(result.get('violence_score', 0), 1),
                    })

                    # Alert on high confidence
                    threshold = get_config().live_detection.alert_threshold
                    if result.get('confidence', 0) >= threshold:
                        emit('live_alert', {
                            'alert_type': 'violence_detected',
                            'confidence': round(result['confidence'], 1),
                            'timestamp': time.strftime('%H:%M:%S'),
                        })
            except Exception as e:
                logger.error(f"Frame analysis error: {e}")

        logger.info("Flask-SocketIO initialized for live detection")

    except ImportError:
        logger.info("flask-socketio not installed, live detection disabled")
        socketio = None


def _register_react_frontend(app: Flask) -> None:
    """Serve React production build at /app route."""
    from flask import send_from_directory
    import os

    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')

    @app.route('/app')
    @app.route('/app/')
    def serve_react():
        if os.path.exists(os.path.join(frontend_dist, 'index.html')):
            return send_from_directory(frontend_dist, 'index.html')
        return 'React frontend not built. Run: cd frontend && npm run build', 404

    @app.route('/app/<path:path>')
    def serve_react_assets(path):
        if os.path.exists(os.path.join(frontend_dist, path)):
            return send_from_directory(frontend_dist, path)
        # SPA fallback: serve index.html for client-side routing
        if os.path.exists(os.path.join(frontend_dist, 'index.html')):
            return send_from_directory(frontend_dist, 'index.html')
        return 'Not found', 404


def _configure_cors(app: Flask, config) -> None:
    """Configure CORS based on environment settings."""
    logger = get_logger(__name__)

    if config.security.cors_allow_all:
        # Development mode - allow all origins (NOT for production)
        logger.warning("CORS configured to allow all origins - use only for development")
        CORS(app)
    else:
        # Production mode - restrict to specific origins
        CORS(
            app,
            origins=config.security.cors_origins,
            supports_credentials=True,
            allow_headers=['Content-Type', 'X-API-Key', 'X-Request-ID'],
            methods=['GET', 'POST', 'OPTIONS']
        )
        logger.info(f"CORS configured for origins: {config.security.cors_origins}")


def _register_error_handlers(app: Flask) -> None:
    """Register application-level error handlers."""
    from .utils.errors import ViolenceDetectionError
    from flask import jsonify
    import uuid

    logger = get_logger(__name__)

    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file too large errors."""
        config = get_config()
        max_mb = config.file.max_content_length // (1024 * 1024)
        return jsonify({
            'success': False,
            'error': 'FileTooLarge',
            'message': f'File too large. Maximum size: {max_mb}MB'
        }), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit errors."""
        return jsonify({
            'success': False,
            'error': 'RateLimitExceeded',
            'message': 'Too many requests. Please try again later.'
        }), 429

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            'success': False,
            'error': 'NotFound',
            'message': 'Resource not found'
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle method not allowed errors."""
        return jsonify({
            'success': False,
            'error': 'MethodNotAllowed',
            'message': 'Method not allowed'
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        error_id = str(uuid.uuid4())[:8]
        logger.exception(f"Internal server error {error_id}")
        return jsonify({
            'success': False,
            'error': 'InternalError',
            'message': 'An unexpected error occurred',
            'error_id': error_id
        }), 500
