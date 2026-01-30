"""
Base analyzer class for Violence Detection System.
Defines the interface for all analyzers.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..utils.logging import get_logger


class BaseAnalyzer(ABC):
    """Abstract base class for content analyzers."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def analyze(self, content: Any) -> Dict[str, Any]:
        """
        Analyze content for violence detection.

        Args:
            content: The content to analyze (text, video path, etc.)

        Returns:
            Dictionary with analysis results including:
            - class: 'Violence' or 'Non-Violence'
            - confidence: float 0-100
            - reasoning: str explanation
            - Additional fields specific to analyzer type
        """
        pass

    def _create_result(
        self,
        is_violent: bool,
        confidence: float,
        reasoning: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a standardized result dictionary.

        Args:
            is_violent: Whether violence was detected
            confidence: Confidence score 0-100
            reasoning: Explanation of the result
            **kwargs: Additional fields to include

        Returns:
            Standardized result dictionary
        """
        result = {
            'class': 'Violence' if is_violent else 'Non-Violence',
            'confidence': float(confidence),
            'reasoning': reasoning,
        }
        result.update(kwargs)
        return result

    def _create_error_result(
        self,
        error: str,
        error_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an error result dictionary.

        Args:
            error: Error message
            error_id: Optional error ID for tracking

        Returns:
            Error result dictionary
        """
        result = {
            'class': 'Error',
            'confidence': 0,
            'error': error,
        }
        if error_id:
            result['error_id'] = error_id
        return result
