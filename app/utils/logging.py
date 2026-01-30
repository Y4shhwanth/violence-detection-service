"""
Structured logging configuration for Violence Detection System.
Replaces print statements with proper logging, including request/response logging.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional
from functools import wraps
import time
import json

from flask import request, g

# Logger cache
_loggers = {}


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name."""
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def setup_logging(
    level: str = 'INFO',
    log_format: Optional[str] = None,
    file_path: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5
) -> None:
    """
    Setup logging configuration for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string
        file_path: Path to log file (optional, logs to stdout if not provided)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers = []

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if path provided
    if file_path:
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress overly verbose loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


class RequestLogger:
    """Middleware for logging HTTP requests and responses."""

    def __init__(self, app=None):
        self.logger = get_logger('request')
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize request logging for Flask app."""
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self):
        """Log request start and set timing."""
        g.request_start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', '')

        self.logger.info(
            'Request started',
            extra={
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'content_length': request.content_length,
            }
        )

    def _after_request(self, response):
        """Log request completion with timing."""
        duration = time.time() - g.get('request_start_time', time.time())

        log_data = {
            'request_id': g.get('request_id', ''),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'content_length': response.content_length,
        }

        if response.status_code >= 400:
            self.logger.warning('Request failed', extra=log_data)
        else:
            self.logger.info('Request completed', extra=log_data)

        return response


def log_performance(logger_name: str = 'performance'):
    """Decorator to log function performance metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.info(
                    f'{func.__name__} completed',
                    extra={
                        'function': func.__name__,
                        'duration_ms': round(duration * 1000, 2),
                        'success': True,
                    }
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f'{func.__name__} failed',
                    extra={
                        'function': func.__name__,
                        'duration_ms': round(duration * 1000, 2),
                        'success': False,
                        'error': str(e),
                    }
                )
                raise

        return wrapper
    return decorator


class StructuredLogger:
    """Logger that outputs structured JSON for production environments."""

    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.name = name

    def _log(self, level: int, message: str, **kwargs):
        """Log with structured data."""
        extra = {'extra_data': json.dumps(kwargs)} if kwargs else {}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._log(logging.ERROR, message, **kwargs)
        self.logger.exception('')
