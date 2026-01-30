"""
Integration tests for API endpoints.
"""
import io
import json
import pytest


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_returns_status(self, client):
        """Test health endpoint returns status field."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestPredictTextEndpoint:
    """Tests for text prediction endpoint."""

    def test_predict_text_no_body(self, client):
        """Test predict_text without body returns 400."""
        response = client.post(
            '/predict_text',
            content_type='application/json',
            data=json.dumps({})
        )
        assert response.status_code == 400

    def test_predict_text_empty_text(self, client):
        """Test predict_text with empty text returns 400."""
        response = client.post(
            '/predict_text',
            content_type='application/json',
            data=json.dumps({'text': ''})
        )
        assert response.status_code == 400

    def test_predict_text_valid(self, client, sample_text_safe, mock_models):
        """Test predict_text with valid text."""
        response = client.post(
            '/predict_text',
            content_type='application/json',
            data=json.dumps({'text': sample_text_safe})
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'prediction' in data
        assert 'confidence' in data


class TestPredictVideoEndpoint:
    """Tests for video prediction endpoint."""

    def test_predict_video_no_file(self, client):
        """Test predict_video without file returns 400."""
        response = client.post('/predict_video')
        assert response.status_code == 400

    def test_predict_video_invalid_extension(self, client):
        """Test predict_video with invalid file type returns 400."""
        data = {
            'video': (io.BytesIO(b"fake content"), 'test.txt')
        }
        response = client.post(
            '/predict_video',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 400


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_security_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get('/health')

        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'

        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'

        assert 'X-XSS-Protection' in response.headers


class TestRateLimitHeaders:
    """Tests for rate limit headers."""

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get('/health')

        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert 'X-RateLimit-Window' in response.headers


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_returns_json(self, client):
        """Test 404 errors return JSON."""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'NotFound'

    def test_405_returns_json(self, client):
        """Test 405 errors return JSON."""
        response = client.get('/predict_text')  # POST-only endpoint
        assert response.status_code == 405
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'MethodNotAllowed'


class TestIndexEndpoints:
    """Tests for index page endpoints."""

    def test_index_returns_200(self, client):
        """Test main index returns 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_old_index_returns_200(self, client):
        """Test old index returns 200."""
        response = client.get('/old')
        assert response.status_code == 200
