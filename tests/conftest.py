"""
Pytest configuration and fixtures for Violence Detection System tests.
"""
import os
import sys
import tempfile
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables before importing app
os.environ['FLASK_DEBUG'] = 'False'
os.environ['CORS_ALLOW_ALL'] = 'True'
os.environ['LAZY_LOAD_MODELS'] = 'True'
os.environ['CACHE_ENABLED'] = 'False'
os.environ['API_KEY_ENABLED'] = 'False'


@pytest.fixture
def app():
    """Create application for testing."""
    from app import create_app

    app = create_app({
        'TESTING': True,
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
    })

    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def sample_text_violent():
    """Sample violent text for testing."""
    return "I will kill you and destroy everything you love"


@pytest.fixture
def sample_text_safe():
    """Sample safe text for testing."""
    return "The weather is beautiful today and I am happy"


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing."""
    # Create minimal valid MP4 file (just the header)
    mp4_header = bytes([
        0x00, 0x00, 0x00, 0x20,  # Box size (32 bytes)
        0x66, 0x74, 0x79, 0x70,  # 'ftyp'
        0x69, 0x73, 0x6F, 0x6D,  # 'isom'
        0x00, 0x00, 0x00, 0x00,  # minor version
        0x69, 0x73, 0x6F, 0x6D,  # 'isom'
        0x61, 0x76, 0x63, 0x31,  # 'avc1'
        0x6D, 0x70, 0x34, 0x31,  # 'mp41'
        0x6D, 0x70, 0x34, 0x32,  # 'mp42'
    ])

    fd, path = tempfile.mkstemp(suffix='.mp4')
    os.write(fd, mp4_header)
    os.close(fd)

    yield path

    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def mock_models(mocker):
    """Mock ML models for faster testing."""
    # Mock text classifier
    mock_text = mocker.patch('app.models.loader.pipeline')
    mock_text.return_value = mocker.MagicMock(
        return_value=[{'label': 'toxic', 'score': 0.9}]
    )

    return mock_text
