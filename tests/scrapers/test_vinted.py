"""
Tests for Vinted scraper.
"""
import pytest
from unittest.mock import patch
from models import Listing
from scrapers.vinted import VintedScraper, _parse_label, _to_float


def _item(label: str, item_id: str) -> str:
    """Build one item the way Vinted escapes it into the catalog page."""
    return (
        r'\"accessibilityLabel\":\"' + label + r'\",'
        r'\"badge\":\"$undefined\",\"actions\":\"$undefined\",'
        r'\"itemId\":\"' + item_id + r'\"}}'
    )


LABEL = (
    "Keen Jasper Zionic dark olive 43, Varemærke: keen, "
    "Artiklens stand: Ny uden prismærker, Størrelse: 43, 895.00 kr, 944.75 kr"
)
PAGE = "<html>" + _item(LABEL, "10074572366") + "</html>"


class TestParsing:
    """The pure parsing helpers."""

    def test_to_float_handles_danish_format(self):
        assert _to_float("1.095,00") == 1095.00
        assert _to_float("895.00") == 895.00
        assert _to_float("not a price") == 0.0

    def test_parse_label_extracts_all_fields(self):
        f = _parse_label(LABEL)
        assert f["title"] == "Keen Jasper Zionic dark olive 43"
        assert f["brand"] == "keen"
        assert f["condition"] == "Ny uden prismærker"
        assert f["size"] == "43"
        assert f["price"] == 895.00
        # second price is the buyer-protection total
        assert f["total_price"] == 944.75

    def test_parse_label_tolerates_missing_fields(self):
        f = _parse_label("Some shoes, 250.00 kr")
        assert f["title"] == "Some shoes, 250.00 kr"
        assert f["brand"] == ""
        assert f["size"] == ""
        # with only one price, the total falls back to it
        assert f["price"] == 250.00
        assert f["total_price"] == 250.00


class TestVintedScraper:
    """Tests for VintedScraper class."""

    def test_vinted_scraper_initialization(self):
        scraper = VintedScraper(debug=False)
        assert scraper.platform == "Vinted"
        assert scraper.name == "vinted-scraper"

    async def test_scrape_parses_catalog_page(self):
        scraper = VintedScraper(debug=False)
        with patch.object(VintedScraper, "_fetch", return_value=[PAGE]):
            listings = await scraper.scrape("Keen Jasper Zionic", max_results=10)

        assert len(listings) == 1
        listing = listings[0]
        assert isinstance(listing, Listing)
        assert listing.platform == "Vinted"
        assert listing.title == "Keen Jasper Zionic dark olive 43"
        assert listing.price == 895.00
        assert listing.currency == "DKK"
        assert listing.url == "https://www.vinted.dk/items/10074572366"
        # size and condition have no home on Listing, so they ride in description
        assert "Size: 43" in listing.description
        assert "Condition: Ny uden prismærker" in listing.description
        assert "944.75" in listing.description

    async def test_scrape_deduplicates_by_item_id(self):
        page = "<html>" + _item(LABEL, "111") + _item(LABEL, "111") + "</html>"
        scraper = VintedScraper(debug=False)
        with patch.object(VintedScraper, "_fetch", return_value=[page]):
            listings = await scraper.scrape("Keen Jasper Zionic", max_results=10)
        assert len(listings) == 1

    async def test_scrape_respects_max_results(self):
        page = "<html>" + "".join(_item(LABEL, str(i)) for i in range(10)) + "</html>"
        scraper = VintedScraper(debug=False)
        with patch.object(VintedScraper, "_fetch", return_value=[page]):
            listings = await scraper.scrape("Keen Jasper Zionic", max_results=3)
        assert len(listings) == 3

    async def test_scrape_drops_loose_matches(self):
        """Vinted's search OR-matches, so irrelevant items must be filtered out."""
        page = "<html>" + _item(
            "Carolyn Keene Kitty And The Talking Robot, 20.00 kr", "222"
        ) + "</html>"
        scraper = VintedScraper(debug=False)
        with patch.object(VintedScraper, "_fetch", return_value=[page]):
            listings = await scraper.scrape("Keen Jasper Zionic", max_results=10)
        assert listings == []

    async def test_scrape_survives_fetch_failure(self):
        scraper = VintedScraper(debug=False)
        with patch.object(VintedScraper, "_fetch", side_effect=RuntimeError("boom")):
            listings = await scraper.scrape("Keen Jasper Zionic", max_results=10)
        assert listings == []

    async def test_scrape_handles_empty_page(self):
        scraper = VintedScraper(debug=False)
        with patch.object(VintedScraper, "_fetch", return_value=["<html></html>"]):
            listings = await scraper.scrape("Keen Jasper Zionic", max_results=10)
        assert listings == []
