"""
Frontend tests for card display.

Tests:
- T079: Frontend test for card display
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
# T079: Frontend test for card display
# =============================================================================

class TestCardDataStructure:
    """Tests for card data structure returned by API."""

    def test_card_data_has_required_fields(self, client):
        """Test that card data has all required fields."""
        mock_listing = MagicMock()
        mock_listing.title = "Card Test Item"
        mock_listing.price = 99.99
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/card"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.95
        mock_listing.score_reason = "Test"
        mock_listing.description = "Card description"
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
            response = client.get("/api/v1/search?query=card+test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

        card = data["results"][0]

        # Required fields for card display
        assert "id" in card
        assert "title" in card
        assert "price" in card
        assert "currency" in card
        assert "original_url" in card
        assert "platform" in card
        assert "image_url" in card

    def test_card_data_has_optional_fields(self, client):
        """Test that card data includes optional fields."""
        mock_listing = MagicMock()
        mock_listing.title = "Optional Fields Item"
        mock_listing.price = 150.0
        mock_listing.currency = "DKK"
        mock_listing.url = "https://example.com/optional"
        mock_listing.platform = "Vinted"
        mock_listing.score = 0.88
        mock_listing.score_reason = "Good match"
        mock_listing.description = "Has optional fields"
        mock_listing.date_posted = "2025-05-19"
        mock_listing.images = []
        mock_listing.review_summary = ""
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=optional+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]

        # Optional fields
        assert "description" in card
        assert "posted_date" in card
        assert "score" in card
        assert "score_reason" in card

    def test_card_data_handles_missing_image(self, client):
        """Test that cards handle missing images gracefully."""
        mock_listing = MagicMock()
        mock_listing.title = "No Image Item"
        mock_listing.price = 50.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/no-image"
        mock_listing.platform = "Tradera"
        mock_listing.score = 0.75
        mock_listing.score_reason = None
        mock_listing.description = "No image"
        mock_listing.date_posted = "2025-05-18"
        mock_listing.images = []  # No images
        mock_listing.review_summary = ""
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=no+image+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]

        # image_url should be None or a placeholder
        assert card["image_url"] is None or len(card["image_url"]) > 0

    def test_card_data_handles_missing_price(self, client):
        """Test that cards handle missing prices gracefully."""
        mock_listing = MagicMock()
        mock_listing.title = "No Price Item"
        mock_listing.price = None  # No price
        mock_listing.currency = None
        mock_listing.url = "https://example.com/no-price"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.70
        mock_listing.score_reason = None
        mock_listing.description = "No price"
        mock_listing.date_posted = "2025-05-17"
        mock_listing.images = []
        mock_listing.review_summary = ""
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=no+price+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]

        # price and currency should be None
        assert card["price"] is None
        assert card["currency"] is None

    def test_card_data_handles_missing_description(self, client):
        """Test that cards handle missing descriptions gracefully."""
        mock_listing = MagicMock()
        mock_listing.title = "No Description Item"
        mock_listing.price = 75.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/no-desc"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.80
        mock_listing.score_reason = None
        mock_listing.description = None  # No description
        mock_listing.date_posted = "2025-05-16"
        mock_listing.images = []
        mock_listing.review_summary = ""
        mock_listing.review_links = []

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=no+desc+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]

        # description should be None
        assert card["description"] is None


class TestCardDisplayFields:
    """Tests for specific card display fields."""

    def test_card_has_platform_field(self, client):
        """Test that cards include platform field."""
        mock_listing = MagicMock()
        mock_listing.title = "Platform Item"
        mock_listing.price = 100.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/platform"
        mock_listing.platform = "Vinted"
        mock_listing.score = 0.90
        mock_listing.score_reason = None
        mock_listing.description = "Test"
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
            response = client.get("/api/v1/search?query=platform+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]
        assert card["platform"] == "Vinted"

    def test_card_has_score_field(self, client):
        """Test that cards include score field."""
        mock_listing = MagicMock()
        mock_listing.title = "Score Item"
        mock_listing.price = 100.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/score"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.98
        mock_listing.score_reason = "Perfect match"
        mock_listing.description = "Test"
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
            response = client.get("/api/v1/search?query=score+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]
        assert card["score"] == 0.98

    def test_card_has_date_field(self, client):
        """Test that cards include date field."""
        mock_listing = MagicMock()
        mock_listing.title = "Date Item"
        mock_listing.price = 100.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/date"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.90
        mock_listing.score_reason = None
        mock_listing.description = "Test"
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
            response = client.get("/api/v1/search?query=date+test")

        assert response.status_code == 200
        data = response.json()
        card = data["results"][0]
        assert card["posted_date"] == "2025-05-20"


class TestCardHoverData:
    """Tests for card hover data (reviews)."""

    def test_card_includes_review_data(self, client):
        """Test that cards can include review data."""
        mock_listing = MagicMock()
        mock_listing.title = "Review Item"
        mock_listing.price = 100.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/review"
        mock_listing.platform = "DBA"
        mock_listing.score = 0.95
        mock_listing.score_reason = None
        mock_listing.description = "Test"
        mock_listing.date_posted = "2025-05-20"
        mock_listing.images = []
        mock_listing.review_summary = "4.8/5 from 35 reviews"
        mock_listing.review_links = ["https://reviews.example.com/1"]

        mock_context = MagicMock()
        mock_context.listings = [mock_listing]

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=review+test")

        assert response.status_code == 200
        data = response.json()

        # Reviews should be in the response
        assert "reviews" in data

    def test_multiple_cards_with_reviews(self, client):
        """Test that multiple cards can have review data."""
        listings = []
        for i in range(3):
            listing = MagicMock()
            listing.title = f"Review Item {i}"
            listing.price = 100.0
            listing.currency = "EUR"
            listing.url = f"https://example.com/review{i}"
            listing.platform = "DBA"
            listing.score = 0.90
            listing.score_reason = None
            listing.description = f"Test {i}"
            listing.date_posted = "2025-05-20"
            listing.images = []
            listing.review_summary = f"{3.0 + i * 0.5}/5 from {10+i} reviews"
            listing.review_links = [f"https://reviews.example.com/{i}"]
            listings.append(listing)

        mock_context = MagicMock()
        mock_context.listings = listings

        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=mock_context)
        mock_pipeline.load_modules = MagicMock()

        with patch('web.backend.api.search.Pipeline', return_value=mock_pipeline):
            response = client.get("/api/v1/search?query=reviews+test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3


class TestCardGridDisplay:
    """Tests for card grid display."""

    def test_multiple_cards_returned(self, client):
        """Test that multiple cards are returned for display."""
        listings = []
        for i in range(10):
            listing = MagicMock()
            listing.title = f"Grid Item {i}"
            listing.price = 50.0 * (i + 1)
            listing.currency = "EUR"
            listing.url = f"https://example.com/grid{i}"
            listing.platform = "DBA" if i % 2 == 0 else "Vinted"
            listing.score = 0.70 + (i * 0.03)
            listing.score_reason = None
            listing.description = f"Grid item {i}"
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
            response = client.get("/api/v1/search?query=grid+test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 10
        assert data["total_results"] == 10

    def test_cards_sorted_by_score(self, client):
        """Test that cards are sorted by score for display."""
        listings = []
        for i in range(5):
            listing = MagicMock()
            listing.title = f"Sorted Item {i}"
            listing.price = 100.0
            listing.currency = "EUR"
            listing.url = f"https://example.com/sorted{i}"
            listing.platform = "DBA"
            listing.score = 0.70 + (i * 0.06)  # Increasing scores
            listing.score_reason = None
            listing.description = f"Sorted {i}"
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
            response = client.get("/api/v1/search?query=sorted+test")

        assert response.status_code == 200
        data = response.json()

        # Verify sorted by score descending
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)
