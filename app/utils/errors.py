"""
Custom exception hierarchy for Violence Detection System.
Provides specific exceptions for different error categories with error IDs for tracking.
"""
import uuid
from typing import Optional, Dict, Any


class ViolenceDetectionError(Exception):
    """Base exception for all violence detection errors."""

    def __init__(
        self,
        message: str,
        error_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_id = error_id or str(uuid.uuid4())[:8]
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_id': self.error_id,
        }

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging (includes details)."""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_id': self.error_id,
            'details': self.details,
        }


class ValidationError(ViolenceDetectionError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Invalid input provided",
        field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field = field
        if field:
            self.details['field'] = field

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.field:
            result['field'] = self.field
        return result


class FileValidationError(ValidationError):
    """Raised when file validation fails (extension, MIME type, magic bytes)."""

    def __init__(
        self,
        message: str = "Invalid file",
        filename: Optional[str] = None,
        expected_types: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, field='file', **kwargs)
        self.filename = filename
        self.expected_types = expected_types
        if filename:
            self.details['filename'] = filename
        if expected_types:
            self.details['expected_types'] = expected_types


class ModelError(ViolenceDetectionError):
    """Raised when model loading or inference fails."""

    def __init__(
        self,
        message: str = "Model error occurred",
        model_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.model_name = model_name
        if model_name:
            self.details['model_name'] = model_name


class AnalysisError(ViolenceDetectionError):
    """Raised when analysis (text, video, audio) fails."""

    def __init__(
        self,
        message: str = "Analysis failed",
        analysis_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.analysis_type = analysis_type
        if analysis_type:
            self.details['analysis_type'] = analysis_type


class RateLimitError(ViolenceDetectionError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details['retry_after'] = retry_after

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.retry_after:
            result['retry_after'] = self.retry_after
        return result


class AuthenticationError(ViolenceDetectionError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(message, **kwargs)


class FileCleanupError(ViolenceDetectionError):
    """Raised when file cleanup fails (non-critical)."""

    def __init__(
        self,
        message: str = "File cleanup failed",
        file_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.file_path = file_path
        if file_path:
            self.details['file_path'] = file_path
