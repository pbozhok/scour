"""
Tests for config module.
"""
import pytest
import os
from unittest.mock import patch
import config


class TestConfig:
    """Tests for configuration loading."""

    def test_exchange_rates_exist(self):
        """Test that exchange rates are defined."""
        assert hasattr(config, 'EXCHANGE_RATES')
        assert isinstance(config.EXCHANGE_RATES, dict)
        assert 'EUR' in config.EXCHANGE_RATES
        assert 'DKK' in config.EXCHANGE_RATES
        assert 'SEK' in config.EXCHANGE_RATES

    def test_exchange_rate_values(self):
        """Test that exchange rate values are positive numbers."""
        for currency, rate in config.EXCHANGE_RATES.items():
            assert isinstance(rate, (int, float))
            assert rate > 0

    def test_eur_base_rate(self):
        """Test that EUR has a base rate of 1.0."""
        assert config.EXCHANGE_RATES['EUR'] == 1.0

    def test_default_currency(self):
        """Test that default currency is defined."""
        assert hasattr(config, 'DEFAULT_CURRENCY')
        assert config.DEFAULT_CURRENCY == "EUR"

    def test_headers_exist(self):
        """Test that HTTP headers are defined."""
        assert hasattr(config, 'HEADERS')
        assert isinstance(config.HEADERS, dict)
        assert 'User-Agent' in config.HEADERS

    def test_scraper_config(self):
        """Test that scraper configuration is defined."""
        assert hasattr(config, 'SCRAPER_TIMEOUT')
        assert isinstance(config.SCRAPER_TIMEOUT, int)
        assert config.SCRAPER_TIMEOUT > 0

    def test_batch_config(self):
        """Test that batch configuration is defined."""
        assert hasattr(config, 'BATCH_SIZE')
        assert hasattr(config, 'DELAY_BETWEEN_BATCHES')
        assert hasattr(config, 'MAX_RETRIES')
        assert isinstance(config.BATCH_SIZE, int)
        assert isinstance(config.DELAY_BETWEEN_BATCHES, float)
        assert isinstance(config.MAX_RETRIES, int)

    def test_review_config(self):
        """Test that review configuration is defined."""
        assert hasattr(config, 'MAX_REVIEW_RESULTS')
        assert hasattr(config, 'REVIEW_DELAY')
        assert isinstance(config.MAX_REVIEW_RESULTS, int)
        assert isinstance(config.REVIEW_DELAY, float)

    def test_default_max_results(self):
        """Test that DEFAULT_MAX_RESULTS is defined."""
        assert hasattr(config, 'DEFAULT_MAX_RESULTS')
        assert isinstance(config.DEFAULT_MAX_RESULTS, int)
        assert config.DEFAULT_MAX_RESULTS > 0
