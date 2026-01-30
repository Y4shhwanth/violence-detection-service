"""
Unit tests for input validators.
"""
import io
import pytest
from werkzeug.datastructures import FileStorage


class TestFileValidator:
    """Tests for FileValidator class."""

    @pytest.fixture
    def validator(self):
        """Create FileValidator instance."""
        from app.api.validators import FileValidator
        return FileValidator()

    def test_validate_no_file(self, validator):
        """Test validation fails for missing file."""
        from app.utils.errors import FileValidationError

        with pytest.raises(FileValidationError):
            validator.validate(None)

    def test_validate_empty_filename(self, validator):
        """Test validation fails for empty filename."""
        from app.utils.errors import FileValidationError

        file = FileStorage(stream=io.BytesIO(b"data"), filename="")
        with pytest.raises(FileValidationError):
            validator.validate(file)

    def test_validate_invalid_extension(self, validator):
        """Test validation fails for invalid extension."""
        from app.utils.errors import FileValidationError

        file = FileStorage(stream=io.BytesIO(b"data"), filename="test.exe")
        with pytest.raises(FileValidationError) as exc_info:
            validator.validate(file)
        assert "not allowed" in str(exc_info.value)

    def test_validate_valid_extension(self, validator):
        """Test validation passes for valid extensions."""
        # Create minimal valid MP4 header
        mp4_header = (
            b'\x00\x00\x00\x20'  # Box size
            b'ftyp'             # Box type
            b'isom'             # Major brand
            b'\x00\x00\x00\x00' # Minor version
            b'isommp41'         # Compatible brands
        )

        for ext in ['mp4', 'avi', 'mov', 'mkv', 'webm']:
            content = mp4_header if ext == 'mp4' else b'\x1a\x45\xdf\xa3' + b'\x00' * 28
            if ext == 'avi':
                content = b'RIFF' + b'\x00' * 4 + b'AVI ' + b'\x00' * 20
            elif ext == 'mov':
                content = mp4_header

            file = FileStorage(
                stream=io.BytesIO(content),
                filename=f"test.{ext}",
                content_type=f"video/{ext}"
            )
            # Should not raise
            is_valid, filename = validator.validate(file)
            assert is_valid


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def limiter(self):
        """Create RateLimiter with small limits for testing."""
        import os
        os.environ['RATE_LIMIT_REQUESTS'] = '3'
        os.environ['RATE_LIMIT_WINDOW'] = '1'

        from app.config import reload_config
        reload_config()

        from app.api.validators import RateLimiter
        return RateLimiter()

    def test_allows_under_limit(self, limiter):
        """Test requests under limit are allowed."""
        assert limiter.check("test-ip") is True
        assert limiter.check("test-ip") is True
        assert limiter.check("test-ip") is True

    def test_blocks_over_limit(self, limiter):
        """Test requests over limit are blocked."""
        from app.utils.errors import RateLimitError

        # Use up the limit
        for _ in range(3):
            limiter.check("test-ip-2")

        # Next request should fail
        with pytest.raises(RateLimitError):
            limiter.check("test-ip-2")

    def test_different_identifiers_separate(self, limiter):
        """Test different identifiers have separate limits."""
        # Use up limit for one identifier
        for _ in range(3):
            limiter.check("ip-1")

        # Different identifier should work
        assert limiter.check("ip-2") is True

    def test_get_remaining(self, limiter):
        """Test getting remaining requests."""
        assert limiter.get_remaining("new-ip") == 3
        limiter.check("new-ip")
        assert limiter.get_remaining("new-ip") == 2


class TestValidateTextInput:
    """Tests for validate_text_input function."""

    def test_empty_text(self):
        """Test empty text raises ValidationError."""
        from app.api.validators import validate_text_input
        from app.utils.errors import ValidationError

        with pytest.raises(ValidationError):
            validate_text_input("")

    def test_none_text(self):
        """Test None raises ValidationError."""
        from app.api.validators import validate_text_input
        from app.utils.errors import ValidationError

        with pytest.raises(ValidationError):
            validate_text_input(None)

    def test_whitespace_only(self):
        """Test whitespace-only text raises ValidationError."""
        from app.api.validators import validate_text_input
        from app.utils.errors import ValidationError

        with pytest.raises(ValidationError):
            validate_text_input("   \n\t  ")

    def test_valid_text(self):
        """Test valid text is returned trimmed."""
        from app.api.validators import validate_text_input

        result = validate_text_input("  Hello World  ")
        assert result == "Hello World"

    def test_text_truncation(self):
        """Test long text is truncated."""
        from app.api.validators import validate_text_input

        long_text = "x" * 20000
        result = validate_text_input(long_text)
        assert len(result) == 10000
