"""
Unit tests for error handling.

Tests:
- T073: Unit test for error handling in web/backend/tests/test_errors.py
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from web.backend.main import app
from web.backend.models.schemas import ErrorResponse


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


# =============================================================================
# T073: Unit test for error handling
# =============================================================================

class TestGlobalExceptionHandler:
    """Tests for the global exception handler."""

    def test_handles_generic_exception(self, client):
        """Test that generic exceptions are caught and return 500."""
        # Trigger an exception by importing a non-existent module
        with patch('web.backend.api.search.Pipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(
                side_effect=Exception("Unexpected error occurred")
            )
            mock_pipeline_class.return_value = mock_pipeline

            response = client.get("/api/v1/search?query=test")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_handles_value_error(self, client):
        """Test that ValueError is caught and returns 400."""
        with patch('web.backend.api.search.Pipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(
                side_effect=ValueError("Invalid configuration")
            )
            mock_pipeline_class.return_value = mock_pipeline

            response = client.get("/api/v1/search?query=test")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"

    def test_handles_timeout_error(self, client):
        """Test that TimeoutError is caught and returns 504."""
        with patch('web.backend.api.search.Pipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(
                side_effect=TimeoutError(30)
            )
            mock_pipeline_class.return_value = mock_pipeline

            response = client.get("/api/v1/search?query=test")

        assert response.status_code == 504
        data = response.json()
        assert data["error"] == "timeout"


class TestErrorResponseStructure:
    """Tests for error response structure."""

    def test_error_response_has_required_fields(self, client):
        """Test that error responses have error, message, and optional details."""
        with patch('web.backend.api.search.Pipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(
                side_effect=Exception("Test error")
            )
            mock_pipeline_class.return_value = mock_pipeline

            response = client.get("/api/v1/search?query=test")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert isinstance(data["error"], str)
        assert isinstance(data["message"], str)

    def test_validation_error_response_structure(self, client):
        """Test that validation errors have correct structure."""
        response = client.get("/api/v1/search?query=")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        if len(data["detail"]) > 0:
            error = data["detail"][0]
            assert "type" in error
            assert "loc" in error
            assert "msg" in error


class TestErrorMessages:
    """Tests for error message content."""

    def test_empty_query_error_message(self, client):
        """Test that empty query returns appropriate error message."""
        response = client.get("/api/v1/search?query=")
        assert response.status_code == 422
        data = response.json()
        assert any(
            "at least 1 character" in str(err).lower() 
            for err in data.get("detail", [])
        )

    def test_long_query_error_message(self, client):
        """Test that query exceeding 500 chars returns appropriate error."""
        long_query = "a" * 501
        response = client.get(f"/api/v1/search?query={long_query}")
        assert response.status_code == 422
        data = response.json()
        assert any(
            "longer than 500" in str(err).lower() or "max_length" in str(err).lower()
            for err in data.get("detail", [])
        )

    def test_invalid_max_results_error_message(self, client):
        """Test that invalid max_results returns appropriate error."""
        response = client.get("/api/v1/search?query=test&max_results=0")
        assert response.status_code == 422
        data = response.json()
        assert any(
            "greater than or equal to 1" in str(err).lower() or "ge" in str(err).lower()
            for err in data.get("detail", [])
        )

    def test_invalid_sort_by_error_message(self, client):
        """Test that invalid sort_by returns appropriate error."""
        response = client.get("/api/v1/search?query=test&sort_by=invalid_sort")
        assert response.status_code == 422
        data = response.json()
        # Check that the error mentions the valid enum values
        assert any(
            "score" in str(err).lower() and "price" in str(err).lower()
            for err in data.get("detail", [])
        )


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Test that health check endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_has_version(self, client):
        """Test that health check includes version."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_html(self, client):
        """Test that root endpoint returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "html" in response.headers["content-type"].lower()

    def test_root_returns_index_content(self, client):
        """Test that root endpoint returns index.html content."""
        response = client.get("/")
        assert response.status_code == 200
        content = response.text
        assert "Scour" in content or "search" in content.lower()


class TestStaticFiles:
    """Tests for static file serving."""

    def test_serves_css_file(self, client):
        """Test that CSS files are served correctly."""
        response = client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"].lower()

    def test_serves_js_file(self, client):
        """Test that JavaScript files are served correctly."""
        response = client.get("/static/js/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"].lower() or \
               "text/plain" in response.headers["content-type"].lower()

    def test_returns_404_for_missing_static_file(self, client):
        """Test that missing static files return 404."""
        response = client.get("/static/css/nonexistent.css")
        assert response.status_code == 404
