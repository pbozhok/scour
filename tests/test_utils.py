"""
Tests for utils module.
"""
import pytest
from utils import extract_json, parse_price


class TestExtractJson:
    """Tests for extract_json function."""

    def test_extract_json_from_string(self):
        """Test extracting JSON from a string."""
        text = 'Some text {"key": "value"} more text'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_with_multiple_objects(self):
        """Test extracting first JSON object when multiple exist."""
        text = '{"first": 1} {"second": 2}'
        result = extract_json(text)
        assert result == {"first": 1}

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        text = '```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_empty_string(self):
        """Test extracting JSON from empty string."""
        result = extract_json("")
        assert result is None

    def test_extract_json_no_json(self):
        """Test extracting JSON from text without JSON."""
        result = extract_json("Plain text without JSON")
        assert result is None

    def test_extract_json_nested(self):
        """Test extracting nested JSON."""
        text = '{"outer": {"inner": "value"}}'
        result = extract_json(text)
        assert result == {"outer": {"inner": "value"}}


class TestParsePrice:
    """Tests for parse_price function."""

    def test_parse_simple_price(self):
        """Test parsing a simple price."""
        assert parse_price("100") == 100.0
        assert parse_price("100.0") == 100.0
        assert parse_price("100,00") == 100.0

    def test_parse_price_with_currency(self):
        """Test parsing price with currency symbol."""
        assert parse_price("100 kr") == 100.0
        assert parse_price("100 kr.") == 100.0
        assert parse_price("100 DKK") == 100.0
        assert parse_price("100 SEK") == 100.0
        assert parse_price("100 EUR") == 100.0

    def test_parse_price_with_spaces(self):
        """Test parsing price with spaces."""
        assert parse_price("1 000") == 1000.0
        assert parse_price("1 000 kr") == 1000.0
        # Note: comma is decimal separator in Danish/European format
        # "1,000" with comma = 1.000 (one point zero), not 1000
        # Use dot or space as thousand separator for DKK: "1.000" or "1 000"

    def test_parse_price_with_decimals(self):
        """Test parsing price with decimals."""
        assert parse_price("99.99") == 99.99
        assert parse_price("99,99") == 99.99
        assert parse_price("99.99 EUR") == 99.99

    def test_parse_price_zero(self):
        """Test parsing zero price."""
        assert parse_price("0") == 0.0
        assert parse_price("0 kr") == 0.0

    def test_parse_price_empty(self):
        """Test parsing empty or invalid price."""
        assert parse_price("") == 0.0
        assert parse_price("N/A") == 0.0
        assert parse_price("free") == 0.0
