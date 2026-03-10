#!/usr/bin/env python3
"""
Violence Detection System Entry Point.

Usage:
    Development: python run.py
    Production:  gunicorn -w 4 -b 0.0.0.0:5001 "app:create_app()"

Environment Variables:
    FLASK_DEBUG     - Enable debug mode (default: False)
    SECRET_KEY      - Flask secret key (auto-generated if not set)
    CORS_ORIGINS    - Comma-separated allowed origins
    CORS_ALLOW_ALL  - Allow all CORS origins (development only)
    API_KEY_ENABLED - Enable API key authentication
    API_KEYS        - Comma-separated valid API keys

See .env.example for full configuration options.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.config import get_config
from app.utils.logging import get_logger
from app.utils.deterministic import set_deterministic


def main():
    """Run the Flask development server."""
    logger = get_logger(__name__)

    # Ensure deterministic inference from the start
    set_deterministic()

    # Create application
    app = create_app()
    config = get_config()

    # Log startup info
    logger.info("=" * 60)
    logger.info("Violence Detection System")
    logger.info("=" * 60)
    logger.info(f"Debug mode: {config.security.debug}")
    logger.info(f"Lazy model loading: {config.model.lazy_load}")
    logger.info(f"Cache enabled: {config.cache.enabled}")
    logger.info(f"Rate limiting: {config.security.rate_limit_requests} req/{config.security.rate_limit_window}s")
    logger.info(f"API auth enabled: {config.security.api_key_enabled}")
    logger.info("=" * 60)

    # Pre-load models if lazy loading is disabled
    if not config.model.lazy_load:
        logger.info("Pre-loading models (lazy loading disabled)...")
        from app.models.loader import get_model_manager
        manager = get_model_manager()
        manager.load_all_models()
        manager.warm_up()
        logger.info("Models loaded and warmed up successfully")

    # Run with SocketIO if available (enables WebSocket for live detection)
    port = int(os.getenv('PORT', 5001))
    from app import socketio
    if socketio is not None:
        logger.info("Starting with Flask-SocketIO (WebSocket enabled)")
        socketio.run(
            app,
            debug=config.security.debug,
            host='0.0.0.0',
            port=port,
            allow_unsafe_werkzeug=True,
        )
    else:
        # Fallback to standard Flask server
        app.run(
            debug=config.security.debug,
            host='0.0.0.0',
            port=port,
            threaded=True,
        )


if __name__ == '__main__':
    main()
