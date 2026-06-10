"""
Tests for keyword_filter module.
"""
import pytest
import asyncio
from models import Listing
from filters.keyword_filter import KeywordFilter


class TestKeywordFilter:
    """Tests for KeywordFilter class."""

    def test_filter_listings_basic_match(self):
        """Test basic keyword matching."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="iPhone 15", price=100.0, currency="EUR", url="url1", description="Great phone", platform="P1"),
            Listing(title="Samsung Galaxy", price=200.0, currency="EUR", url="url2", description="Android phone", platform="P2"),
            Listing(title="iPhone 15 Case", price=50.0, currency="EUR", url="url3", description="Phone case", platform="P3"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone 15", {}))
        # Should match listings with "iPhone" and "15" keywords
        assert len(result) == 2
        assert all(l.relevant for l in result)

    def test_filter_listings_partial_match(self):
        """Test partial keyword matching."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="iPhone 15", price=100.0, currency="EUR", url="url1", description="Great phone", platform="P1"),
            Listing(title="Samsung Galaxy", price=200.0, currency="EUR", url="url2", description="Android phone", platform="P2"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone", {}))
        assert len(result) == 1
        assert result[0].title == "iPhone 15"

    def test_filter_listings_description_match(self):
        """Test matching keywords in description."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="Phone", price=100.0, currency="EUR", url="url1", description="This is an iPhone 15", platform="P1"),
            Listing(title="Another Phone", price=200.0, currency="EUR", url="url2", description="This is a Samsung", platform="P2"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone 15", {}))
        assert len(result) == 1
        assert result[0].title == "Phone"

    def test_filter_listings_multi_word_query(self):
        """Test multi-word query matching."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="iPhone 15 Pro", price=100.0, currency="EUR", url="url1", description="Latest iPhone", platform="P1"),
            Listing(title="iPhone 15", price=200.0, currency="EUR", url="url2", description="iPhone", platform="P2"),
            Listing(title="Samsung", price=300.0, currency="EUR", url="url3", description="Android", platform="P3"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone 15", {}))
        # Should match listings with at least 1 keyword (15 has 2 keywords, so need at least 1)
        assert len(result) >= 2

    def test_filter_listings_no_matches_fallback(self):
        """Test fallback when no matches found."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="Samsung", price=100.0, currency="EUR", url="url1", description="Android", platform="P1"),
            Listing(title="Google Pixel", price=200.0, currency="EUR", url="url2", description="Android phone", platform="P2"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone", {}))
        # Should fallback to including all listings
        assert len(result) == 2
        assert all(l.relevant for l in result)
        assert all("Fallback" in l.relevance_reason for l in result)

    def test_filter_listings_empty_list(self):
        """Test filtering empty list."""
        filter_obj = KeywordFilter()
        result = asyncio.run(filter_obj.filter([], "test", {}))
        assert result == []

    def test_filter_listings_case_insensitive(self):
        """Test case-insensitive matching."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="IPHONE 15", price=100.0, currency="EUR", url="url1", description="", platform="P1"),
            Listing(title="iphone 15", price=200.0, currency="EUR", url="url2", description="", platform="P2"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone 15", {}))
        assert len(result) == 2

    def test_filter_listings_relevance_reason(self):
        """Test that relevance reason is set."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="iPhone 15", price=100.0, currency="EUR", url="url1", description="Great phone", platform="P1"),
        ]
        result = asyncio.run(filter_obj.filter(listings, "iPhone 15", {}))
        assert result[0].relevant is True
        assert "keyword" in result[0].relevance_reason.lower()

    def test_filter_listings_three_keywords(self):
        """Test matching with three keywords."""
        filter_obj = KeywordFilter()
        listings = [
            Listing(title="iPhone 15 Pro", price=100.0, currency="EUR", url="url1", description="Latest phone", platform="P1"),
            Listing(title="iPhone 15", price=200.0, currency="EUR", url="url2", description="phone", platform="P2"),
        ]
        # Query with 3 keywords: need at least 2 matches (3//2 = 1, max(1, 1) = 1)
        result = asyncio.run(filter_obj.filter(listings, "iPhone 15 Pro", {}))
        # First listing has all 3 keywords
        assert result[0].title == "iPhone 15 Pro"
