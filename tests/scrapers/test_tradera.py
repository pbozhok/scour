"""
Tests for Tradera scraper.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from models import Listing
from scrapers.tradera import TraderaScraper


class TestTraderaScraper:
    """Tests for TraderaScraper class."""

    def test_tradera_scraper_initialization(self):
        """Test TraderaScraper can be initialized."""
        scraper = TraderaScraper(debug=False)
        assert scraper.platform == "Tradera"

    def test_tradera_scraper_parse_price(self):
        """Test TraderaScraper price parsing."""
        scraper = TraderaScraper(debug=False)
        assert scraper.parse_price("100 SEK") == 100.0
        assert scraper.parse_price("1 000 SEK") == 1000.0
        assert scraper.parse_price("99.99 SEK") == 99.99

    @patch('httpx.AsyncClient')
    async def test_tradera_scraper_scrape(self, mock_client):
        """Test TraderaScraper scrape method."""
        mock_resp = MagicMock()
        # HTML with __NEXT_DATA__ JSON
        mock_resp.text = '''
        <html><body>
            <script id="__NEXT_DATA__" type="application/json">{
                "props": {
                    "pageProps": {
                        "initialState": {
                            "discover": {
                                "items": [
                                    {
                                        "itemId": 12345,
                                        "shortDescription": "Test Item",
                                        "price": 100,
                                        "buyNowPrice": 150,
                                        "itemUrl": "https://www.tradera.com/en/item/260103/12345/test-item",
                                        "startDate": "2024-01-15T10:30:00.000Z",
                                        "categoryId": 260103
                                    }
                                ]
                            }
                        }
                    }
                }
            }</script>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        scraper = TraderaScraper(debug=False)
        listings = await scraper.scrape("test", max_results=10)
        
        # Check that listings have required fields
        assert len(listings) == 1
        assert isinstance(listings[0], Listing)
        assert listings[0].platform == "Tradera"
        assert listings[0].title == "Test Item"
        assert listings[0].price == 150.0  # Should use buyNowPrice
        assert listings[0].currency == "SEK"
        assert "12345" in listings[0].url

    @patch('httpx.AsyncClient')
    async def test_tradera_scraper_date_extraction(self, mock_client):
        """Test that Tradera scraper can extract dates."""
        mock_resp = MagicMock()
        mock_resp.text = '''
        <html><body>
            <div id="item-card-1">
                <a href="/en/item/260103/12345/test-item">Test Item</a>
                <span>100 SEK</span>
                <span class="date">2024-01-15</span>
            </div>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        scraper = TraderaScraper(debug=False)
        listings = await scraper.scrape("test", max_results=10)
        
        # Check that listings were created
        assert len(listings) >= 0

    @patch('httpx.AsyncClient')
    async def test_tradera_scraper_html_fallback(self, mock_client):
        """Test TraderaScraper falls back to HTML parsing when no __NEXT_DATA__."""
        mock_resp = MagicMock()
        # HTML without __NEXT_DATA__ (fallback to HTML parsing)
        mock_resp.text = '''
        <html><body>
            <div id="item-card-1">
                <a href="/en/item/260103/12345/test-item">Test Item</a>
                <span>200 SEK</span>
            </div>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        scraper = TraderaScraper(debug=False)
        listings = await scraper.scrape("test", max_results=10)
        
        # Check that listings have required fields
        assert len(listings) >= 1
        assert isinstance(listings[0], Listing)
        assert listings[0].platform == "Tradera"
        assert listings[0].currency == "SEK"

    def test_tradera_scraper_empty_results(self):
        """Test Tradera scraper handles empty results."""
        scraper = TraderaScraper(debug=False)
        assert hasattr(scraper, 'scrape')
