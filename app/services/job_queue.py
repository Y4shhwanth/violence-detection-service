"""
Job queue for async analysis processing.
Uses in-memory dict/queue with optional Redis backend.
"""
import uuid
import time
import threading
import queue
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Job:
    """Represents an analysis job."""
    id: str
    status: str = 'queued'  # queued, processing, completed, failed
    progress: int = 0
    current_step: str = ''
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    video_path: Optional[str] = None
    text_input: Optional[str] = None


class JobQueue:
    """In-memory job queue with background worker threads."""

    _instance: Optional['JobQueue'] = None
    _lock = threading.Lock()

    def __new__(cls, max_workers: int = 2, job_ttl: int = 3600):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_workers: int = 2, job_ttl: int = 3600):
        if self._initialized:
            return
        self._jobs: Dict[str, Job] = {}
        self._queue: queue.Queue = queue.Queue()
        self._max_workers = max_workers
        self._job_ttl = job_ttl
        self._workers: list = []
        self._handler: Optional[Callable] = None
        self._initialized = True
        logger.info(f"JobQueue initialized: max_workers={max_workers}, job_ttl={job_ttl}")

    def set_handler(self, handler: Callable):
        """Set the job processing handler function."""
        self._handler = handler

    def start_workers(self):
        """Start background worker threads."""
        for i in range(self._max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f'job-worker-{i}')
            t.start()
            self._workers.append(t)
        logger.info(f"Started {self._max_workers} worker threads")

    def _worker_loop(self):
        """Worker thread main loop."""
        while True:
            try:
                job_id = self._queue.get(timeout=5)
            except queue.Empty:
                self._cleanup_expired()
                continue

            job = self._jobs.get(job_id)
            if not job or not self._handler:
                continue

            try:
                job.status = 'processing'
                job.current_step = 'Starting analysis'
                job.updated_at = time.time()

                result = self._handler(job)
                job.result = result
                job.status = 'completed'
                job.progress = 100
                job.current_step = 'Complete'
            except Exception as e:
                logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                job.status = 'failed'
                job.error = str(e)
            finally:
                job.updated_at = time.time()
                self._queue.task_done()

    def submit_job(self, video_path: Optional[str] = None, text_input: Optional[str] = None) -> str:
        """Submit a new analysis job. Returns job_id."""
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, video_path=video_path, text_input=text_input)
        self._jobs[job_id] = job
        self._queue.put(job_id)
        logger.info(f"Job submitted: {job_id}")
        return job_id

    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            'job_id': job.id,
            'status': job.status,
            'progress': job.progress,
            'current_step': job.current_step,
            'created_at': job.created_at,
            'updated_at': job.updated_at,
            'error': job.error,
        }

    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job result (only available when completed)."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        if job.status != 'completed':
            return {'status': job.status, 'progress': job.progress}
        return job.result

    def update_job(self, job_id: str, progress: int = None, current_step: str = None):
        """Update job progress."""
        job = self._jobs.get(job_id)
        if not job:
            return
        if progress is not None:
            job.progress = progress
        if current_step is not None:
            job.current_step = current_step
        job.updated_at = time.time()

    def _cleanup_expired(self):
        """Remove expired jobs."""
        now = time.time()
        expired = [
            jid for jid, job in self._jobs.items()
            if now - job.created_at > self._job_ttl and job.status in ('completed', 'failed')
        ]
        for jid in expired:
            del self._jobs[jid]


_job_queue: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """Get global JobQueue instance."""
    global _job_queue
    if _job_queue is None:
        from ..config import get_config
        config = get_config()
        jq_config = getattr(config, 'job_queue', None)
        max_workers = getattr(jq_config, 'max_workers', 2) if jq_config else 2
        job_ttl = getattr(jq_config, 'job_ttl', 3600) if jq_config else 3600
        _job_queue = JobQueue(max_workers=max_workers, job_ttl=job_ttl)
    return _job_queue
