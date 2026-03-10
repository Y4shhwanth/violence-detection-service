"""
Result caching for Violence Detection System.
Caches analysis results by file hash to avoid redundant processing.
"""
import hashlib
import time
from typing import Optional, Dict, Any
from collections import OrderedDict
from threading import Lock

from ..config import get_config


class ResultCache:
    """
    LRU cache for analysis results with TTL support.
    Thread-safe implementation using locks.
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600
    ):
        """
        Initialize the cache.

        Args:
            max_size: Maximum number of entries to store
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = Lock()

    def _generate_key(self, file_content: bytes, analysis_type: str) -> str:
        """Generate a cache key from file content hash and analysis type."""
        file_hash = hashlib.sha256(file_content).hexdigest()
        return f"{analysis_type}:{file_hash}"

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if a cache entry has expired."""
        if self.ttl_seconds == 0:
            return False
        return time.time() - entry['timestamp'] > self.ttl_seconds

    def get(
        self,
        file_content: bytes,
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached result if it exists and hasn't expired.

        Args:
            file_content: The file content to generate hash from
            analysis_type: Type of analysis (text, video, audio)

        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(file_content, analysis_type)

        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            if self._is_expired(entry):
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry['result']

    def get_by_hash(
        self,
        file_hash: str,
        analysis_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached result using pre-computed file hash.

        Args:
            file_hash: Pre-computed SHA256 hash of file content
            analysis_type: Type of analysis (text, video, audio)

        Returns:
            Cached result or None if not found/expired
        """
        key = f"{analysis_type}:{file_hash}"

        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            if self._is_expired(entry):
                del self._cache[key]
                return None

            self._cache.move_to_end(key)
            return entry['result']

    def set(
        self,
        file_content: bytes,
        analysis_type: str,
        result: Dict[str, Any]
    ) -> str:
        """
        Store a result in the cache.

        Args:
            file_content: The file content to generate hash from
            analysis_type: Type of analysis (text, video, audio)
            result: The analysis result to cache

        Returns:
            The cache key (file hash)
        """
        key = self._generate_key(file_content, analysis_type)
        file_hash = key.split(':')[1]

        with self._lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = {
                'result': result,
                'timestamp': time.time(),
            }

        return file_hash

    def set_by_hash(
        self,
        file_hash: str,
        analysis_type: str,
        result: Dict[str, Any]
    ) -> None:
        """
        Store a result using pre-computed file hash.

        Args:
            file_hash: Pre-computed SHA256 hash of file content
            analysis_type: Type of analysis (text, video, audio)
            result: The analysis result to cache
        """
        key = f"{analysis_type}:{file_hash}"

        with self._lock:
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)

            self._cache[key] = {
                'result': result,
                'timestamp': time.time(),
            }

    def invalidate(self, file_content: bytes, analysis_type: str) -> bool:
        """
        Remove a specific entry from the cache.

        Args:
            file_content: The file content to generate hash from
            analysis_type: Type of analysis

        Returns:
            True if entry was found and removed, False otherwise
        """
        key = self._generate_key(file_content, analysis_type)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_frame_result(
        self,
        video_hash: str,
        frame_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Get a cached frame-level analysis result."""
        key = f"frame:{video_hash}:{frame_idx}"
        with self._lock:
            if key not in self._cache:
                return None
            entry = self._cache[key]
            if self._is_expired(entry):
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return entry['result']

    def set_frame_result(
        self,
        video_hash: str,
        frame_idx: int,
        result: Dict[str, Any]
    ) -> None:
        """Cache a frame-level analysis result."""
        key = f"frame:{video_hash}:{frame_idx}"
        with self._lock:
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = {
                'result': result,
                'timestamp': time.time(),
            }

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
            }


# Global cache instance
_cache: Optional[ResultCache] = None


def get_cache() -> ResultCache:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        config = get_config()
        _cache = ResultCache(
            max_size=config.cache.max_size,
            ttl_seconds=config.cache.ttl_seconds
        )
    return _cache


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hex-encoded SHA256 hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()
