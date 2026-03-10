"""Utility modules for Violence Detection System."""
from .errors import (
    ViolenceDetectionError,
    ValidationError,
    FileValidationError,
    ModelError,
    AnalysisError,
    RateLimitError,
    AuthenticationError,
)
from .logging import get_logger, setup_logging
from .cache import ResultCache, get_cache
from .policy_engine import PolicyEngine, get_policy_engine
from .llm_explainer import LLMExplainer, get_llm_explainer

# Lazy imports for modules with heavy dependencies (torch, numpy)
def get_explainability_engine():
    from .explainability import get_explainability_engine as _get
    return _get()

def set_deterministic(seed=42):
    from .deterministic import set_deterministic as _set
    return _set(seed)

def inference_context(model=None):
    from .deterministic import inference_context as _ctx
    return _ctx(model)

__all__ = [
    'ViolenceDetectionError',
    'ValidationError',
    'FileValidationError',
    'ModelError',
    'AnalysisError',
    'RateLimitError',
    'AuthenticationError',
    'get_logger',
    'setup_logging',
    'ResultCache',
    'get_cache',
    'PolicyEngine',
    'get_policy_engine',
    'LLMExplainer',
    'get_llm_explainer',
    'get_explainability_engine',
    'set_deterministic',
    'inference_context',
]
