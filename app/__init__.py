"""
Violence Detection System Flask Application Factory.
Creates and configures the Flask application with all security features.
"""
import os
from flask import Flask
from flask_cors import CORS

from .config import get_config
from .utils.logging import setup_logging, RequestLogger, get_logger
from .api.routes import api_bp


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

    # Register blueprints
    app.register_blueprint(api_bp)

    # Register error handlers at app level
    _register_error_handlers(app)

    logger.info(
        "Flask application created",
        debug=config.security.debug,
        cors_origins=config.security.cors_origins if not config.security.cors_allow_all else ['*']
    )

    return app


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
