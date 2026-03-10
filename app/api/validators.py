"""
Input validation and security checks for Violence Detection System.
Includes file validation, rate limiting, and authentication.
"""
import os
import time
import hashlib
from functools import wraps
from typing import Optional, Dict, Set, Tuple
from collections import defaultdict
from threading import Lock

from flask import request, g
from werkzeug.datastructures import FileStorage

from ..config import get_config
from ..utils.errors import (
    FileValidationError,
    ValidationError,
    RateLimitError,
    AuthenticationError,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FileValidator:
    """Validates uploaded files for security and correctness."""

    # Magic bytes for common video formats
    MAGIC_BYTES = {
        'mp4': [
            (b'ftyp', 4, 8),  # ISO Base Media file (MPEG-4) Part 12
            (b'moov', 4, 8),  # Older MP4
            (b'mdat', 4, 8),  # MP4 data
        ],
        'avi': [(b'RIFF', 0, 4), (b'AVI ', 8, 12)],
        'mkv': [(b'\x1a\x45\xdf\xa3', 0, 4)],
        'webm': [(b'\x1a\x45\xdf\xa3', 0, 4)],
        'mov': [
            (b'ftyp', 4, 8),
            (b'moov', 4, 8),
            (b'free', 4, 8),
            (b'wide', 4, 8),
        ],
    }

    def __init__(self):
        self.config = get_config().file

    def validate(self, file: FileStorage) -> Tuple[bool, str]:
        """
        Validate an uploaded file.

        Args:
            file: The uploaded file

        Returns:
            Tuple of (is_valid, filename or error message)

        Raises:
            FileValidationError: If validation fails
        """
        if not file or not file.filename:
            raise FileValidationError("No file provided")

        filename = file.filename

        # Validate extension
        self._validate_extension(filename)

        # Validate MIME type
        self._validate_mimetype(file)

        # Validate magic bytes
        self._validate_magic_bytes(file)

        # Validate file size (content length header)
        self._validate_size()

        return True, filename

    def _validate_extension(self, filename: str) -> None:
        """Validate file extension."""
        ext = self._get_extension(filename)
        if ext not in self.config.allowed_video_extensions:
            raise FileValidationError(
                f"File type not allowed. Allowed: {', '.join(self.config.allowed_video_extensions)}",
                filename=filename,
                expected_types=list(self.config.allowed_video_extensions)
            )

    def _validate_mimetype(self, file: FileStorage) -> None:
        """Validate MIME type."""
        mimetype = file.content_type or ''

        # Allow empty mimetype (will be validated by magic bytes)
        if not mimetype:
            return

        if mimetype not in self.config.allowed_video_mimetypes:
            # Log warning but don't reject - magic bytes are more reliable
            logger.warning(
                f"Unexpected MIME type: {mimetype} for file: {file.filename}"
            )

    def _validate_magic_bytes(self, file: FileStorage) -> None:
        """Validate file magic bytes to prevent disguised uploads."""
        ext = self._get_extension(file.filename)

        # Read first 32 bytes for magic byte check
        header = file.read(32)
        file.seek(0)  # Reset file position

        if len(header) < 12:
            raise FileValidationError(
                "File too small to be a valid video",
                filename=file.filename
            )

        # Check magic bytes for the extension
        if ext in self.MAGIC_BYTES:
            valid = False
            for magic, start, end in self.MAGIC_BYTES[ext]:
                if header[start:end] == magic:
                    valid = True
                    break

            if not valid:
                # Special handling for MP4/MOV - check if it starts with valid box
                if ext in ('mp4', 'mov'):
                    # MP4/MOV files should have a box size in first 4 bytes
                    # followed by box type (ftyp, moov, free, etc.)
                    box_type = header[4:8]
                    valid_boxes = [b'ftyp', b'moov', b'free', b'mdat', b'wide', b'skip', b'pnot']
                    if box_type in valid_boxes:
                        valid = True

                if not valid:
                    raise FileValidationError(
                        "File content does not match expected format",
                        filename=file.filename
                    )

    def _validate_size(self) -> None:
        """Validate file size from Content-Length header."""
        content_length = request.content_length
        if content_length and content_length > self.config.max_content_length:
            raise FileValidationError(
                f"File too large. Maximum size: {self.config.max_content_length // (1024*1024)}MB"
            )

    def _get_extension(self, filename: str) -> str:
        """Get lowercase file extension."""
        if '.' not in filename:
            return ''
        return filename.rsplit('.', 1)[1].lower()


class RateLimiter:
    """
    In-memory rate limiter using sliding window.
    For production, use Redis-based rate limiting.
    """

    def __init__(self):
        self.config = get_config().security
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def check(self, identifier: str) -> bool:
        """
        Check if request should be allowed.

        Args:
            identifier: Client identifier (IP address, API key, etc.)

        Returns:
            True if request is allowed

        Raises:
            RateLimitError: If rate limit exceeded
        """
        now = time.time()
        window_start = now - self.config.rate_limit_window

        with self._lock:
            # Clean old requests
            self._requests[identifier] = [
                t for t in self._requests[identifier]
                if t > window_start
            ]

            if len(self._requests[identifier]) >= self.config.rate_limit_requests:
                # Calculate retry-after
                oldest = min(self._requests[identifier])
                retry_after = int(oldest + self.config.rate_limit_window - now) + 1

                raise RateLimitError(
                    f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    retry_after=retry_after
                )

            self._requests[identifier].append(now)
            return True

    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        now = time.time()
        window_start = now - self.config.rate_limit_window

        with self._lock:
            self._requests[identifier] = [
                t for t in self._requests[identifier]
                if t > window_start
            ]
            return self.config.rate_limit_requests - len(self._requests[identifier])


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def validate_api_key(f):
    """
    Decorator to validate API key if authentication is enabled.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        config = get_config().security

        if not config.api_key_enabled:
            return f(*args, **kwargs)

        api_key = request.headers.get('X-API-Key')
        if not api_key:
            raise AuthenticationError("API key required")

        if api_key not in config.api_keys:
            raise AuthenticationError("Invalid API key")

        g.api_key = api_key
        return f(*args, **kwargs)

    return decorated


def rate_limit(f):
    """
    Decorator to apply rate limiting.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        limiter = get_rate_limiter()

        # Use IP address as identifier (or API key if authenticated)
        identifier = getattr(g, 'api_key', None) or request.remote_addr

        limiter.check(identifier)

        # Add rate limit headers to response
        remaining = limiter.get_remaining(identifier)
        g.rate_limit_remaining = remaining

        return f(*args, **kwargs)

    return decorated


def add_rate_limit_headers(response):
    """Add rate limit headers to response."""
    config = get_config().security
    remaining = getattr(g, 'rate_limit_remaining', config.rate_limit_requests)

    response.headers['X-RateLimit-Limit'] = str(config.rate_limit_requests)
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Window'] = str(config.rate_limit_window)

    return response


def validate_text_input(text: Optional[str]) -> str:
    """
    Validate text input.

    Args:
        text: Input text

    Returns:
        Validated text

    Raises:
        ValidationError: If validation fails
    """
    if not text:
        raise ValidationError("No text provided", field='text')

    text = text.strip()
    if not text:
        raise ValidationError("Text cannot be empty", field='text')

    # Limit text length (prevent DoS)
    max_length = 10000
    if len(text) > max_length:
        text = text[:max_length]
        logger.warning(f"Text truncated to {max_length} characters")

    return text
