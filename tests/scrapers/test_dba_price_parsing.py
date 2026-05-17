"""
Test for DBA price parsing of the specific ad: https://www.dba.dk/recommerce/forsale/item/19563469
This tests that "12.999 kr" is correctly parsed as 12999.0 DKK
"""
import pytest
from utils import parse_price


class TestDBAPriceParsing:
    """Tests for DBA price parsing, specifically for Danish number formats."""

    def test_price_12999_dkk_from_ad(self):
        """Test that 12.999 kr (from ad 19563469) is parsed as 12999.0."""
        assert parse_price("12.999 kr") == 12999.0

    def test_price_5000_dkk(self):
        """Test that 5.000 kr is parsed as 5000.0."""
        assert parse_price("5.000 kr") == 5000.0

    def test_price_without_currency(self):
        """Test price without currency symbol."""
        assert parse_price("12.999") == 12999.0
        assert parse_price("12999") == 12999.0

    def test_price_with_space_separator(self):
        """Test price with space as thousand separator."""
        assert parse_price("12 999 kr") == 12999.0
        assert parse_price("5 000 kr") == 5000.0

    def test_price_with_decimal(self):
        """Test price with decimal separator."""
        assert parse_price("12999,99 kr") == 12999.99
        assert parse_price("12.999,99 kr") == 12999.99

    def test_price_mixed_separators(self):
        """Test price with both thousand and decimal separators."""
        # Danish: 1.299,99 = 1299.99
        assert parse_price("1.299,99 kr") == 1299.99

    def test_price_from_parent_text(self):
        """Test price extracted from parent text containing the price."""
        # Simulating the actual text from the DBA search page
        parent_text = "12.999 kr.MAC MINI M4 16/256 med sk\u00e6rm"
        # The price should be extracted correctly
        assert parse_price(parent_text) == 12999.0

    def test_price_from_complex_text(self):
        """Test price extraction from complex text with multiple numbers."""
        text = "MAC MINI M4 16/256 med skærm 27\", 12.999 kr"
        assert parse_price(text) == 12999.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
