"""
Tests for utils module.
"""
import pytest
from utils import extract_json, parse_price, normalize_model_name


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


class TestNormalizeModelName:
    """Tests for normalize_model_name function."""

    def test_normalize_basic(self):
        """Test basic model name normalization."""
        assert normalize_model_name("Pixel 9a") == "pixel9a"
        assert normalize_model_name("Pixel 9A") == "pixel9a"
        assert normalize_model_name("Google Pixel 9a") == "pixel9a"

    def test_normalize_with_spaces(self):
        """Test normalization of spaces in model names."""
        assert normalize_model_name("Pixel 9 a") == "pixel9a"
        assert normalize_model_name("Pixel  9a") == "pixel9a"

    def test_normalize_with_dashes(self):
        """Test normalization of dashes in model names."""
        assert normalize_model_name("Pixel-9a") == "pixel9a"
        assert normalize_model_name("Pixel-9-a") == "pixel9a"

    def test_normalize_iphone(self):
        """Test iPhone model normalization."""
        assert normalize_model_name("iPhone 15") == "iphone15"
        assert normalize_model_name("Apple iPhone 15") == "iphone15"
        assert normalize_model_name("iPhone 15 Pro") == "iphone15pro"
        assert normalize_model_name("Apple iPhone 15 Pro Max") == "iphone15promax"

    def test_normalize_galaxy(self):
        """Test Samsung Galaxy model normalization."""
        assert normalize_model_name("Samsung Galaxy S23") == "galaxys23"
        assert normalize_model_name("Galaxy S23 Ultra") == "galaxys23ultra"
        assert normalize_model_name("Samsung Galaxy S23+") == "galaxys23+"

    def test_normalize_empty(self):
        """Test normalization of empty string."""
        assert normalize_model_name("") == ""
        assert normalize_model_name("   ") == ""

    def test_normalize_case_insensitive(self):
        """Test that normalization is case-insensitive."""
        assert normalize_model_name("PIXEL 9A") == "pixel9a"
        assert normalize_model_name("pixel 9a") == "pixel9a"
        assert normalize_model_name("GoOgLe PiXeL 9A") == "pixel9a"

    def test_normalize_other_brands(self):
        """Test normalization of other brand models."""
        assert normalize_model_name("MacBook Pro M3") == "macbookprom3"
        assert normalize_model_name("Apple MacBook Pro M3") == "macbookprom3"
        assert normalize_model_name("Sony WH-1000XM5") == "wh1000xm5"
