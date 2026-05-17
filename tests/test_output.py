"""
Tests for output module.
"""
import pytest
from rich.console import Console
from models import Listing
from output import display_results


class TestDisplayResults:
    """Tests for display_results function."""

    def test_display_results_empty_list(self, capsys):
        """Test displaying empty results."""
        display_results([], "test query")
        captured = capsys.readouterr()
        assert "No relevant listings found" in captured.out

    def test_display_results_single_listing(self, capsys):
        """Test displaying a single listing."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
            score=8.5,
            score_reason="Good value",
        )
        display_results([listing], "test query")
        captured = capsys.readouterr()
        assert "Test Item" in captured.out
        assert "100 EUR" in captured.out
        assert "8.5 / 10" in captured.out

    def test_display_results_multiple_listings(self, capsys):
        """Test displaying multiple listings."""
        listings = [
            Listing(
                title=f"Item {i}",
                price=100.0 * i,
                currency="EUR",
                url=f"https://example.com/{i}",
                description=f"Description {i}",
                platform="Platform",
                score=7.0 + i,
            )
            for i in range(3)
        ]
        display_results(listings, "test query")
        captured = capsys.readouterr()
        assert "Item 0" in captured.out
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "#1" in captured.out
        assert "#2" in captured.out
        assert "#3" in captured.out

    def test_display_results_with_review_summary(self, capsys):
        """Test displaying listings with review summary."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
            review_summary="Great product with excellent reviews",
        )
        display_results([listing], "test query")
        captured = capsys.readouterr()
        assert "Great product with excellent reviews" in captured.out

    def test_display_results_with_review_links(self, capsys):
        """Test displaying listings with review links."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
            review_links=["https://review1.com", "https://review2.com"],
        )
        display_results([listing], "test query")
        captured = capsys.readouterr()
        assert "https://review1.com" in captured.out
        assert "https://review2.com" in captured.out

    def test_display_results_skip_reviews(self, capsys):
        """Test displaying with skip_reviews=True."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
            product_model="Model X",
        )
        display_results([listing], "test query", skip_reviews=True)
        captured = capsys.readouterr()
        # Model should still be shown when skip_reviews is True
        # but the test is mainly to ensure no errors
        assert "Test Item" in captured.out

    def test_display_results_with_product_model(self, capsys):
        """Test displaying listings with product model."""
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="https://example.com",
            description="Test description",
            platform="TestPlatform",
            product_model="iPhone 15 Pro",
        )
        display_results([listing], "test query")
        captured = capsys.readouterr()
        assert "iPhone 15 Pro" in captured.out
