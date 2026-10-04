"""
Tests for description fetcher.
"""
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from models import Listing
from processors.description_fetcher import DescriptionFetcher


def _client_returning(html: str) -> MagicMock:
    """An httpx.AsyncClient stand-in whose get() yields `html`."""
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status = MagicMock()  # called synchronously by the fetcher
    client = MagicMock()
    client.get = AsyncMock(return_value=resp)
    return client


def _listing(platform: str, url: str) -> Listing:
    return Listing(
        title="Test",
        price=100.0,
        currency="DKK",
        url=url,
        description="",
        platform=platform,
    )


JSON_LD = '''
<html><body>
    <script type="application/ld+json">
        {"description": "%s"}
    </script>
</body></html>
'''


class TestDescriptionFetcher:
    """Tests for DescriptionFetcher class."""

    def test_description_fetcher_initialization(self):
        """Test DescriptionFetcher can be initialized."""
        fetcher = DescriptionFetcher(debug=False)
        assert fetcher.debug is False

    async def test_fetch_description_dba(self):
        """DBA descriptions come from the JSON-LD block when present."""
        client = _client_returning(JSON_LD % "Test description from JSON-LD")
        listing = _listing("DBA", "https://dba.dk/test")

        fetcher = DescriptionFetcher(debug=False)
        await fetcher._fetch_description_dba(listing, client, asyncio.Semaphore(1))

        assert "Test description from JSON-LD" in listing.description

    async def test_fetch_description_dba_fallback(self):
        """With no JSON-LD, DBA falls back to a description div."""
        client = _client_returning(
            '<html><body><div class="description">Test description from div</div></body></html>'
        )
        listing = _listing("DBA", "https://dba.dk/test")

        fetcher = DescriptionFetcher(debug=False)
        await fetcher._fetch_description_dba(listing, client, asyncio.Semaphore(1))

        assert "Test description from div" in listing.description

    async def test_fetch_description_vinted(self):
        """Test fetching Vinted description."""
        client = _client_returning(JSON_LD % "Test Vinted description")
        listing = _listing("Vinted", "https://vinted.dk/test")

        fetcher = DescriptionFetcher(debug=False)
        await fetcher._fetch_description_vinted(listing, client, asyncio.Semaphore(1))

        assert "Test Vinted description" in listing.description

    async def test_fetch_description_tradera(self):
        """Test fetching Tradera description."""
        client = _client_returning(
            '<html><body><div class="description">Test Tradera description</div></body></html>'
        )
        listing = _listing("Tradera", "https://tradera.com/test")

        fetcher = DescriptionFetcher(debug=False)
        await fetcher._fetch_description_tradera(listing, client, asyncio.Semaphore(1))

        assert "Test Tradera description" in listing.description

    async def test_fetch_description_survives_http_error(self):
        """A failing request must not propagate out of the fetcher."""
        client = MagicMock()
        client.get = AsyncMock(side_effect=RuntimeError("connection reset"))
        listing = _listing("DBA", "https://dba.dk/test")

        fetcher = DescriptionFetcher(debug=False)
        await fetcher._fetch_description_dba(listing, client, asyncio.Semaphore(1))

        assert listing.description == ""

    async def test_fetch_descriptions_multiple(self):
        """Test that process() dispatches to per-platform fetchers for all listings."""
        fetcher = DescriptionFetcher(debug=False)
        listings = [
            _listing("DBA", "https://dba.dk/test1"),
            _listing("DBA", "https://dba.dk/test2"),
        ]

        async def fake_fetch(listing, client, sem):
            listing.description = "fetched desc"

        with patch.object(fetcher, "_fetch_description_dba", side_effect=fake_fetch):
            result = await fetcher.process(listings, {})

        assert all(l.description == "fetched desc" for l in result)

    async def test_process_skips_listings_that_already_have_descriptions(self):
        """Listings with a description must not be re-fetched."""
        fetcher = DescriptionFetcher(debug=False)
        already = _listing("DBA", "https://dba.dk/kept")
        already.description = "already here"

        async def fake_fetch(listing, client, sem):  # pragma: no cover - must not run
            listing.description = "overwritten"

        with patch.object(fetcher, "_fetch_description_dba", side_effect=fake_fetch):
            result = await fetcher.process([already], {})

        assert result[0].description == "already here"
