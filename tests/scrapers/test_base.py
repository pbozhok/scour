"""
Tests for base scraper class.
"""
import asyncio
import pytest
from scrapers.base import BaseScraper
from models import Listing


class _StubScraper(BaseScraper):
    """Minimal concrete subclass for testing BaseScraper behaviour."""
    name = "stub-scraper"
    platform = "Stub"

    async def scrape(self, query: str, max_results: int = 10) -> list:
        return []


class TestBaseScraper:
    """Tests for BaseScraper class."""

    def test_base_scraper_initialization(self):
        scraper = _StubScraper(debug=False)
        assert scraper.debug is False
        assert hasattr(scraper, 'platform')
        assert hasattr(scraper, 'headers')

    def test_base_scraper_debug_mode(self):
        scraper = _StubScraper(debug=True)
        assert scraper.debug is True

    def test_parse_price(self):
        scraper = _StubScraper(debug=False)
        assert scraper.parse_price("100") == 100.0
        assert scraper.parse_price("100 kr") == 100.0
        assert scraper.parse_price("1 000 DKK") == 1000.0
        assert scraper.parse_price("99.99") == 99.99

    def test_parse_price_edge_cases(self):
        scraper = _StubScraper(debug=False)
        assert scraper.parse_price("") == 0.0
        assert scraper.parse_price("free") == 0.0
        assert scraper.parse_price("N/A") == 0.0

    def test_log_debug(self):
        scraper = _StubScraper(debug=True)
        scraper.log_debug("Test message")

    def test_scrape_method_exists(self):
        scraper = _StubScraper(debug=False)
        assert hasattr(scraper, 'scrape')
        result = asyncio.run(scraper.scrape("test"))
        assert result == []
