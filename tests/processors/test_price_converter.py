"""
Tests for price converter.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from models import Listing
from processors.price_converter import PriceConverter


class TestPriceConverter:
    """Tests for PriceConverter class."""

    def test_price_converter_initialization(self):
        """Test PriceConverter can be initialized."""
        converter = PriceConverter(debug=False)
        result = converter.initialize({"target_currency": "EUR"})
        assert result is True
        assert converter.debug is False

    async def test_convert_prices_same_currency(self):
        """Test converting prices when currency is already target."""
        converter = PriceConverter(debug=False)
        converter.initialize({"target_currency": "EUR"})
        listings = [
            Listing(title="Test", price=100.0, currency="EUR", url="", description="", platform="Test"),
            Listing(title="Test2", price=200.0, currency="EUR", url="", description="", platform="Test"),
        ]

        await converter.process(listings, {"target_currency": "EUR"})

        assert listings[0].currency == "EUR"
        assert listings[0].price == 100.0
        assert listings[1].currency == "EUR"
        assert listings[1].price == 200.0

    async def test_convert_prices_dkk_to_eur(self):
        """Test converting DKK prices to EUR."""
        converter = PriceConverter(debug=False)
        converter.initialize({"target_currency": "EUR"})
        listings = [
            Listing(title="Test", price=745.0, currency="DKK", url="", description="", platform="Test"),
        ]

        await converter.process(listings, {"target_currency": "EUR"})

        # 745 DKK should be approximately 100 EUR (rate is ~7.45)
        assert listings[0].currency == "EUR"
        assert abs(listings[0].price - 100.0) < 0.1

    async def test_convert_prices_sek_to_eur(self):
        """Test converting SEK prices to EUR."""
        converter = PriceConverter(debug=False)
        converter.initialize({"target_currency": "EUR"})
        listings = [
            Listing(title="Test", price=1120.0, currency="SEK", url="", description="", platform="Test"),
        ]

        await converter.process(listings, {"target_currency": "EUR"})

        # 1120 SEK should be approximately 100 EUR (rate is ~11.20)
        assert listings[0].currency == "EUR"
        assert abs(listings[0].price - 100.0) < 0.1

    async def test_convert_prices_empty_list(self):
        """Test converting empty list of listings."""
        converter = PriceConverter(debug=False)
        converter.initialize({"target_currency": "EUR"})
        listings = []

        result = await converter.process(listings, {"target_currency": "EUR"})

        assert result == []

    async def test_convert_prices_all_same_currency(self):
        """Test converting when all listings already have target currency."""
        converter = PriceConverter(debug=False)
        converter.initialize({"target_currency": "EUR"})
        listings = [
            Listing(title="Test1", price=100.0, currency="EUR", url="", description="", platform="Test"),
            Listing(title="Test2", price=200.0, currency="EUR", url="", description="", platform="Test"),
        ]

        await converter.process(listings, {"target_currency": "EUR"})

        assert all(l.currency == "EUR" for l in listings)
        assert all(l.price > 0 for l in listings)
