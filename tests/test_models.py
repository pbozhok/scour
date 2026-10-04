"""
Tests for models module.
"""
import pytest
from dataclasses import fields
from models import Listing


class TestListing:
    """Tests for the Listing dataclass."""

    def test_listing_default_values(self):
        """Test that Listing has correct default values."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
        )

        assert listing.title == "Test Item"
        assert listing.price == 100.0
        assert listing.currency == "EUR"
        assert listing.url == "https://example.com"
        assert listing.description == "Test description"
        assert listing.platform == "TestPlatform"
        assert listing.images == []
        assert listing.relevant is False
        assert listing.relevance_reason == ""
        assert listing.product_model == ""
        assert listing.review_summary == ""
        assert listing.review_links == []
        assert listing.score == 0.0
        assert listing.score_reason == ""
        assert listing.date_posted == ""

    def test_listing_with_all_fields(self):
        """Test Listing with all fields populated."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
            images=["image1.jpg", "image2.jpg"],
            relevant=True,
            relevance_reason="Test reason",
            product_model="Test Model",
            review_summary="Great product",
            review_links=["link1", "link2"],
            score=9.5,
            score_reason="High quality",
            date_posted="2024-01-15",
        )

        assert listing.images == ["image1.jpg", "image2.jpg"]
        assert listing.relevant is True
        assert listing.relevance_reason == "Test reason"
        assert listing.product_model == "Test Model"
        assert listing.review_summary == "Great product"
        assert listing.review_links == ["link1", "link2"]
        assert listing.score == 9.5
        assert listing.score_reason == "High quality"
        assert listing.date_posted == "2024-01-15"

    def test_listing_field_count(self):
        """Test that Listing has the expected number of fields."""
        num_fields = len(fields(Listing))
        # title, price, currency, url, description, platform, images,
        # relevant, relevance_reason, product_model, review_summary,
        # review_links, score, score_reason, date_posted, location
        assert num_fields == 16
