"""
GPU optimization utilities.
AMP context manager, batch processing, GPU memory management.
"""
import torch
from contextlib import contextmanager
from typing import List, Any, Callable

from .logging import get_logger

logger = get_logger(__name__)


class GPUOptimizer:
    """GPU optimization and mixed precision utilities."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.cuda_available = torch.cuda.is_available()
        self.device = torch.device('cuda' if self.cuda_available else 'cpu')
        self._initialized = True

        if self.cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            logger.info(f"GPU available: {gpu_name} ({gpu_memory:.1f}GB)")
        else:
            logger.info("No GPU available, using CPU")

    @contextmanager
    def amp_context(self):
        """Automatic Mixed Precision context for faster inference."""
        if self.cuda_available:
            with torch.cuda.amp.autocast():
                yield
        else:
            yield

    def batch_inference(self, items: List[Any], inference_fn: Callable, batch_size: int = 8) -> List[Any]:
        """Run inference in batches for efficiency."""
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            with torch.no_grad():
                if self.cuda_available:
                    with torch.cuda.amp.autocast():
                        batch_results = inference_fn(batch)
                else:
                    batch_results = inference_fn(batch)
                results.extend(batch_results if isinstance(batch_results, list) else [batch_results])
        return results

    def clear_gpu_memory(self):
        """Free GPU memory."""
        if self.cuda_available:
            torch.cuda.empty_cache()
            logger.info("GPU memory cleared")

    def get_memory_stats(self) -> dict:
        """Get GPU memory usage statistics."""
        if not self.cuda_available:
            return {'gpu_available': False}

        return {
            'gpu_available': True,
            'gpu_name': torch.cuda.get_device_name(0),
            'allocated_mb': round(torch.cuda.memory_allocated(0) / (1024**2), 1),
            'reserved_mb': round(torch.cuda.memory_reserved(0) / (1024**2), 1),
            'max_allocated_mb': round(torch.cuda.max_memory_allocated(0) / (1024**2), 1),
        }


_gpu_optimizer = None


def get_gpu_optimizer() -> GPUOptimizer:
    global _gpu_optimizer
    if _gpu_optimizer is None:
        _gpu_optimizer = GPUOptimizer()
    return _gpu_optimizer
