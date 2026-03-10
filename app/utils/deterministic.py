"""
Deterministic inference utilities for Violence Detection System.

Ensures reproducible results by setting all random seeds and providing
an inference context manager that disables dropout and gradient computation.
"""
import random
from contextlib import contextmanager
from typing import Optional

import numpy as np

from .logging import get_logger

logger = get_logger(__name__)


def set_deterministic(seed: int = 42) -> None:
    """
    Set all random seeds and torch deterministic flags for reproducible inference.

    Args:
        seed: Random seed to use across all generators.
    """
    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch
        torch.manual_seed(seed)

        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        logger.warning("PyTorch not available, skipping torch deterministic settings")

    logger.info(f"Deterministic mode enabled (seed={seed})")


@contextmanager
def inference_context(model: Optional[object] = None):
    """
    Context manager for deterministic inference.

    Sets model to eval mode and disables gradient computation.

    Args:
        model: Optional torch model or HuggingFace pipeline to set to eval mode.
    """
    try:
        import torch
    except ImportError:
        yield
        return

    if model is not None:
        # Handle HuggingFace pipeline objects
        underlying = getattr(model, 'model', model)
        if hasattr(underlying, 'eval'):
            underlying.eval()

    with torch.no_grad():
        yield
