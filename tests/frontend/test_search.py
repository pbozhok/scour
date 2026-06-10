"""
Frontend tests for search flow.

Tests:
- T078: Frontend test for search flow
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from web.backend.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


# =============================================================================
# T078: Frontend test for search flow
# =============================================================================

class TestFrontendSearchPage:
    """Tests for the frontend search page."""

    def test_page_loads_successfully(self, client):
        """Test that the search page loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert "html" in response.headers["content-type"].lower()

    def test_page_contains_search_form(self, client):
        """Test that the page contains a search form."""
        response = client.get("/")
        html = response.text
        assert "<form" in html or "form" in html.lower()
        assert "search" in html.lower()

    def test_page_contains_search_input(self, client):
        """Test that the page contains a search input field."""
        response = client.get("/")
        html = response.text
        assert "input" in html.lower()
        assert "query" in html.lower() or "search" in html.lower()

    def test_page_contains_submit_button(self, client):
        """Test that the page contains a submit button."""
        response = client.get("/")
        html = response.text
        assert "button" in html.lower() or "submit" in html.lower()

    def test_page_contains_results_container(self, client):
        """Test that the page contains a results container."""
        response = client.get("/")
        html = response.text
        assert "results" in html.lower() or "container" in html.lower()

    def test_page_contains_loading_indicator(self, client):
        """Test that the page contains a loading indicator."""
        response = client.get("/")
        html = response.text
        assert "loading" in html.lower() or "spinner" in html.lower() or "search-animation" in html.lower()

    def test_page_contains_error_message_area(self, client):
        """Test that the page contains an error message area."""
        response = client.get("/")
        html = response.text
        assert "error" in html.lower()

    def test_page_links_to_css(self, client):
        """Test that the page links to CSS file."""
        response = client.get("/")
        html = response.text
        assert "styles.css" in html

    def test_page_links_to_js(self, client):
        """Test that the page links to JavaScript file."""
        response = client.get("/")
        html = response.text
        assert "app.js" in html


class TestFrontendAssets:
    """Tests for frontend assets."""

    def test_css_file_served(self, client):
        """Test that CSS file is served correctly."""
        response = client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert len(response.text) > 0

    def test_js_file_served(self, client):
        """Test that JavaScript file is served correctly."""
        response = client.get("/static/js/app.js")
        assert response.status_code == 200
        assert len(response.text) > 0

    def test_css_contains_search_styles(self, client):
        """Test that CSS contains search-related styles."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert ".search-container" in css or "search" in css.lower()

    def test_css_contains_card_styles(self, client):
        """Test that CSS contains card-related styles."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert ".card" in css or "card" in css.lower()

    def test_js_contains_search_function(self, client):
        """Test that JavaScript contains search function."""
        response = client.get("/static/js/app.js")
        js = response.text
        assert "submitSearch" in js or "search" in js.lower()

    def test_js_contains_fetch(self, client):
        """Test that JavaScript uses fetch API for requests."""
        response = client.get("/static/js/app.js")
        js = response.text
        assert "fetch" in js.lower()


class TestFrontendInteractions:
    """Tests for frontend user interactions."""

    def test_api_returns_search_form_structure(self, client):
        """Test that API response can be used by frontend."""
        mock_listing = MagicMock()
        mock_listing.title = "Frontend Test Item"
        mock_listing.price = 99.99
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/frontend"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.95
        mock_listing.score_reason = "Frontend test"
        mock_listing.description = "Frontend test description"
        mock_listing.date_posted = "2025-05-20"
        mock_listing.images = ["https://example.com/image.jpg"]
        mock_listing.review_summary = "4.5/5"
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=frontend+test")

        assert response.status_code == 200
        data = response.json()

        # Verify frontend can use this data
        assert "query" in data
        assert "results" in data
        if data["results"]:
            result = data["results"][0]
            assert "title" in result
            assert "price" in result
            assert "original_url" in result

    def test_api_returns_sortable_data(self, client):
        """Test that API returns data that can be sorted by frontend."""
        listings = []
        for i in range(3):
            listing = MagicMock()
            listing.title = f"Item {i}"
            listing.price = 50.0 * (i + 1)
            listing.currency = "EUR"
            listing.url = f"https://example.com/{i}"
            listing.platform = "DBA"
            listing.score = 0.8 + (i * 0.05)
            listing.score_reason = None
            listing.description = f"Desc {i}"
            listing.date_posted = "2025-05-20"
            listing.images = []
            listing.review_summary = ""
            listing.review_links = []
            listings.append(listing)

        mock_context = MagicMock()
        mock_context.listings = listings

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=sortable+test")

        assert response.status_code == 200
        data = response.json()

        # Verify each result has sortable fields
        for result in data["results"]:
            assert "price" in result
            assert "score" in result
            assert "posted_date" in result or "date" in str(result).lower()

    def test_api_returns_filterable_data(self, client):
        """Test that API returns data with filter states."""
        mock_context = MagicMock()
        mock_context.listings = []

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=filterable+test&use_filter=false")

        assert response.status_code == 200
        data = response.json()

        # Verify toggles are present
        assert "toggles" in data
        assert "filtering" in data["toggles"]
        assert "reviewing" in data["toggles"]
        assert "scoring" in data["toggles"]

    def test_empty_results_response(self, client):
        """Test that empty results are handled correctly for frontend."""
        mock_context = MagicMock()
        mock_context.listings = []

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=empty+test")

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0
        assert len(data["results"]) == 0
        # Frontend can display "no results found" message


class TestFrontendStateManagement:
    """Tests for frontend state management."""

    def test_api_response_includes_all_state_fields(self, client):
        """Test that API response includes all fields needed for frontend state."""
        mock_context = MagicMock()
        mock_context.listings = []

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=state+test")

        assert response.status_code == 200
        data = response.json()

        # Verify all state fields are present
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
        assert "sort_by" in data
        assert "toggles" in data
        assert "timestamp" in data
        assert "reviews" in data
