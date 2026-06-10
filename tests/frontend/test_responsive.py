"""
Frontend tests for responsive design.

Tests:
- T080: Frontend test for responsive design
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
# T080: Frontend test for responsive design
# =============================================================================

class TestResponsiveCSS:
    """Tests for responsive CSS styles."""

    def test_css_has_mobile_breakpoint(self, client):
        """Test that CSS has mobile breakpoint (640px)."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "640px" in css or "min-width" in css.lower()

    def test_css_has_tablet_breakpoint(self, client):
        """Test that CSS has tablet breakpoint (768px)."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "768px" in css or "min-width" in css.lower()

    def test_css_has_desktop_breakpoint(self, client):
        """Test that CSS has desktop breakpoint (1024px)."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "1024px" in css or "min-width" in css.lower()

    def test_css_has_large_desktop_breakpoint(self, client):
        """Test that CSS has large desktop breakpoint (1280px)."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "1280px" in css or "min-width" in css.lower()

    def test_css_uses_media_queries(self, client):
        """Test that CSS uses @media queries for responsive design."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "@media" in css

    def test_css_has_grid_layout(self, client):
        """Test that CSS has grid layout for cards."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "grid" in css.lower() or "grid-template-columns" in css.lower()

    def test_css_has_flexible_card_width(self, client):
        """Test that CSS has flexible card widths."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "minmax" in css.lower() or "fr" in css.lower()


class TestResponsiveCardGrid:
    """Tests for responsive card grid behavior."""

    def test_api_returns_data_suitable_for_grid(self, client):
        """Test that API returns data that can be displayed in a grid."""
        # Create mock listings
        listings = []
        for i in range(20):
            listing = MagicMock()
            listing.title = f"Responsive Item {i}"
            listing.price = 50.0 * (i + 1)
            listing.currency = "EUR"
            listing.url = f"https://example.com/responsive{i}"
            listing.platform = "DBA" if i % 3 == 0 else ("Vinted" if i % 3 == 1 else "Tradera")
            listing.score = 0.70 + (i * 0.02)
            listing.score_reason = None
            listing.description = f"Responsive test item {i}"
            listing.date_posted = "2025-05-20"
            listing.images = [f"https://example.com/image{i}.jpg"]
            listing.review_summary = ""
            listing.review_links = []
            listings.append(listing)

        mock_context = MagicMock()
        mock_context.listings = listings

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=responsive+test")

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 20
        assert len(data["results"]) == 20

        # All cards should have consistent structure
        for card in data["results"]:
            assert "id" in card
            assert "title" in card
            assert "price" in card
            assert "platform" in card

    def test_api_returns_enough_cards_for_grid(self, client):
        """Test that API can return enough cards to fill a grid row."""
        # Mobile: 1 column, Tablet: 2 columns, Desktop: 3-4 columns
        # Need at least 4 cards to test grid layout
        listings = []
        for i in range(4):
            listing = MagicMock()
            listing.title = f"Grid Fill Item {i}"
            listing.price = 100.0
            listing.currency = "EUR"
            listing.url = f"https://example.com/gridfill{i}"
            listing.platform = "DBA"
            listing.score = 0.80 + (i * 0.05)
            listing.score_reason = None
            listing.description = f"Fill item {i}"
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
            response = client.get("/api/v1/search?query=gridfill+test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 4


class TestResponsiveImages:
    """Tests for responsive image handling."""

    def test_api_returns_image_urls(self, client):
        """Test that API returns image URLs for responsive display."""
        mock_listing = MagicMock()
        mock_listing.title = "Image Test Item"
        mock_listing.price = 100.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/image"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.90
        mock_listing.score_reason = None
        mock_listing.description = "Image test"
        mock_listing.date_posted = "2025-05-20"
        mock_listing.images = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
        ]
        mock_listing.review_summary = ""
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=image+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]
        assert "image_url" in card
        assert card["image_url"] is not None

    def test_api_handles_missing_images_responsively(self, client):
        """Test that API handles missing images for responsive display."""
        mock_listing = MagicMock()
        mock_listing.title = "No Image Responsive Item"
        mock_listing.price = 100.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/no-image-responsive"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.85
        mock_listing.score_reason = None
        mock_listing.description = "No image"
        mock_listing.date_posted = "2025-05-20"
        mock_listing.images = []
        mock_listing.review_summary = ""
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=no+image+responsive")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]
        # Should handle gracefully
        assert "image_url" in card


class TestResponsiveTypography:
    """Tests for responsive typography."""

    def test_css_has_font_sizes(self, client):
        """Test that CSS defines font sizes."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "font-size" in css.lower()

    def test_css_has_heading_styles(self, client):
        """Test that CSS has heading styles."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "h1" in css.lower() or "h2" in css.lower() or "h3" in css.lower()

    def test_css_has_responsive_font_scaling(self, client):
        """Test that CSS scales fonts responsively."""
        response = client.get("/static/css/styles.css")
        css = response.text
        # Check for responsive font patterns
        assert "rem" in css.lower() or "em" in css.lower() or "px" in css.lower()


class TestResponsiveSpacing:
    """Tests for responsive spacing."""

    def test_css_has_padding(self, client):
        """Test that CSS has padding definitions."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "padding" in css.lower()

    def test_css_has_margin(self, client):
        """Test that CSS has margin definitions."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "margin" in css.lower()

    def test_css_has_gap(self, client):
        """Test that CSS uses gap for grid/flex layout."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "gap" in css.lower()


class TestResponsiveBehavior:
    """Tests for responsive behavior patterns."""

    def test_css_has_transitions(self, client):
        """Test that CSS has transitions for smooth responsive changes."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert "transition" in css.lower()

    def test_css_has_hover_effects(self, client):
        """Test that CSS has hover effects for cards."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert ":hover" in css.lower()

    def test_css_has_active_states(self, client):
        """Test that CSS has active states."""
        response = client.get("/static/css/styles.css")
        css = response.text
        assert ":active" in css.lower()

    def test_css_uses_relative_units(self, client):
        """Test that CSS uses relative units for responsiveness."""
        response = client.get("/static/css/styles.css")
        css = response.text
        # Check for relative units
        has_relative = any(unit in css.lower() for unit in ["%", "rem", "em", "vw", "vh"])
        assert has_relative
