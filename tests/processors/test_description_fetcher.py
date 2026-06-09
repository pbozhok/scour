"""
Tests for description fetcher.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup
from models import Listing
from processors.description_fetcher import DescriptionFetcher


class TestDescriptionFetcher:
    """Tests for DescriptionFetcher class."""

    def test_description_fetcher_initialization(self):
        """Test DescriptionFetcher can be initialized."""
        fetcher = DescriptionFetcher(debug=False)
        assert fetcher.debug is False

    @patch('httpx.AsyncClient')
    async def test_fetch_description_dba(self, mock_client):
        """Test fetching DBA description."""
        mock_resp = MagicMock()
        mock_resp.text = '''
        <html><body>
            <script type="application/ld+json">
                {"description": "Test description from JSON-LD"}
            </script>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        fetcher = DescriptionFetcher(debug=False)
        listing = Listing(
            title="Test",
            price=100.0,
            currency="DKK",
            url="https://dba.dk/test",
            description="",
            platform="DBA"
        )
        
        await fetcher._fetch_description_dba(listing)
        
        assert "Test description from JSON-LD" in listing.description

    @patch('httpx.AsyncClient')
    async def test_fetch_description_dba_fallback(self, mock_client):
        """Test fetching DBA description with div fallback."""
        mock_resp = MagicMock()
        mock_resp.text = '''
        <html><body>
            <div class="description">Test description from div</div>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        fetcher = DescriptionFetcher(debug=False)
        listing = Listing(
            title="Test",
            price=100.0,
            currency="DKK",
            url="https://dba.dk/test",
            description="",
            platform="DBA"
        )
        
        await fetcher._fetch_description_dba(listing)
        
        assert "Test description from div" in listing.description

    @patch('httpx.AsyncClient')
    async def test_fetch_description_vinted(self, mock_client):
        """Test fetching Vinted description."""
        mock_resp = MagicMock()
        mock_resp.text = '''
        <html><body>
            <script type="application/ld+json">
                {"description": "Test Vinted description"}
            </script>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        fetcher = DescriptionFetcher(debug=False)
        listing = Listing(
            title="Test",
            price=100.0,
            currency="DKK",
            url="https://vinted.dk/test",
            description="",
            platform="Vinted"
        )
        
        await fetcher._fetch_description_vinted(listing)
        
        assert "Test Vinted description" in listing.description

    @patch('httpx.AsyncClient')
    async def test_fetch_description_tradera(self, mock_client):
        """Test fetching Tradera description."""
        mock_resp = MagicMock()
        mock_resp.text = '''
        <html><body>
            <div class="description">Test Tradera description</div>
        </body></html>
        '''
        mock_resp.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)
        
        fetcher = DescriptionFetcher(debug=False)
        listing = Listing(
            title="Test",
            price=100.0,
            currency="SEK",
            url="https://tradera.com/test",
            description="",
            platform="Tradera"
        )
        
        await fetcher._fetch_description_tradera(listing)
        
        assert "Test Tradera description" in listing.description

    async def test_fetch_descriptions_multiple(self):
        """Test that process() dispatches to per-platform fetchers for all listings."""
        fetcher = DescriptionFetcher(debug=False)
        listings = [
            Listing(title="Test1", price=100.0, currency="DKK", url="https://dba.dk/test1", description="", platform="DBA"),
            Listing(title="Test2", price=200.0, currency="DKK", url="https://dba.dk/test2", description="", platform="DBA"),
        ]

        async def fake_fetch(listing):
            listing.description = "fetched desc"

        with patch.object(fetcher, "_fetch_description_dba", side_effect=fake_fetch):
            result = await fetcher.process(listings, {})

        assert all(l.description == "fetched desc" for l in result)
