"""
Unit tests for ResultCache.
"""
import time
import pytest


class TestResultCache:
    """Tests for ResultCache class."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        from app.utils.cache import ResultCache
        return ResultCache(max_size=10, ttl_seconds=1)

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        content = b"test content"
        result = {'class': 'Violence', 'confidence': 85.0}

        cache.set(content, 'text', result)
        retrieved = cache.get(content, 'text')

        assert retrieved == result

    def test_get_nonexistent(self, cache):
        """Test getting non-existent key returns None."""
        result = cache.get(b"nonexistent", 'text')
        assert result is None

    def test_ttl_expiration(self, cache):
        """Test that entries expire after TTL."""
        content = b"test content"
        result = {'class': 'Non-Violence', 'confidence': 90.0}

        cache.set(content, 'text', result)
        assert cache.get(content, 'text') is not None

        # Wait for TTL to expire
        time.sleep(1.5)
        assert cache.get(content, 'text') is None

    def test_max_size_eviction(self, cache):
        """Test that oldest entries are evicted when max size reached."""
        # Fill cache to capacity
        for i in range(10):
            cache.set(f"content{i}".encode(), 'text', {'id': i})

        # Add one more - should evict oldest
        cache.set(b"content_new", 'text', {'id': 'new'})

        # First entry should be evicted
        assert cache.get(b"content0", 'text') is None
        # New entry should exist
        assert cache.get(b"content_new", 'text') is not None

    def test_invalidate(self, cache):
        """Test invalidating a cache entry."""
        content = b"test content"
        result = {'class': 'Violence', 'confidence': 85.0}

        cache.set(content, 'text', result)
        assert cache.get(content, 'text') is not None

        removed = cache.invalidate(content, 'text')
        assert removed is True
        assert cache.get(content, 'text') is None

    def test_clear(self, cache):
        """Test clearing all cache entries."""
        for i in range(5):
            cache.set(f"content{i}".encode(), 'text', {'id': i})

        count = cache.clear()
        assert count == 5
        assert cache.stats()['size'] == 0

    def test_stats(self, cache):
        """Test cache statistics."""
        for i in range(3):
            cache.set(f"content{i}".encode(), 'text', {'id': i})

        stats = cache.stats()
        assert stats['size'] == 3
        assert stats['max_size'] == 10
        assert stats['ttl_seconds'] == 1

    def test_different_analysis_types(self, cache):
        """Test that same content with different analysis types are separate."""
        content = b"test content"
        text_result = {'type': 'text'}
        video_result = {'type': 'video'}

        cache.set(content, 'text', text_result)
        cache.set(content, 'video', video_result)

        assert cache.get(content, 'text') == text_result
        assert cache.get(content, 'video') == video_result

    def test_by_hash_methods(self, cache):
        """Test get_by_hash and set_by_hash methods."""
        file_hash = "abc123def456"
        result = {'class': 'Violence'}

        cache.set_by_hash(file_hash, 'video', result)
        retrieved = cache.get_by_hash(file_hash, 'video')

        assert retrieved == result
