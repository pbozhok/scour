"""
Tests for llm_filter module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from models import Listing
from filters.llm_filter import LLMFilter


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat = AsyncMock()
    return mock


class TestLLMFilter:
    """Tests for LLMFilter class."""

    def test_llm_filter_initialization(self, mock_llm_client):
        """Test LLMFilter initialization."""
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        assert filter_obj.llm_client == mock_llm_client
        assert filter_obj.debug is False

    def test_llm_filter_debug_mode(self, mock_llm_client):
        """Test LLMFilter with debug mode."""
        filter_obj = LLMFilter(mock_llm_client, debug=True)
        assert filter_obj.debug is True

    def test_filter_listings_empty_list(self, mock_llm_client):
        """Test filtering empty list."""
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        result = asyncio.run(filter_obj.filter_listings([], "test query"))
        assert result == []

    def test_filter_listings_all_irrelevant_fallback(self, mock_llm_client):
        """Test fallback when all listings are marked as irrelevant by LLM."""
        # Mock response where all items are marked as not relevant
        mock_response = '{"results": [{"id": 0, "relevant": false, "reason": "Not relevant"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query"))
        # Should fallback to marking all as relevant
        assert len(result) == 1
        assert result[0].relevant is True
        assert "Fallback" in result[0].relevance_reason

    def test_filter_listings_with_llm_response(self, mock_llm_client):
        """Test filtering with valid LLM response."""
        mock_response = '{"results": [{"id": 0, "relevant": true, "reason": "Matches query well"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query"))
        assert len(result) == 1
        assert result[0].relevant is True
        assert result[0].relevance_reason == "Matches query well"

    def test_filter_listings_with_list_response(self, mock_llm_client):
        """Test filtering with LLM returning a list instead of dict."""
        mock_response = '[{"id": 0, "relevant": true, "reason": "Good match"}]'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query"))
        assert len(result) == 1
        assert result[0].relevant is True

    def test_filter_listings_with_error_fallback(self, mock_llm_client):
        """Test filtering with LLM error (should fallback to all relevant)."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query", max_retries=1))
        assert len(result) == 2
        assert all(l.relevant for l in result)

    def test_filter_listings_multiple_batches(self, mock_llm_client):
        """Test filtering with multiple batches."""
        mock_response = '{"results": [{"id": 0, "relevant": true, "reason": "Good"}, {"id": 1, "relevant": false, "reason": "Bad"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title=f"Item {i}", price=100.0, currency="EUR", url=f"url{i}", description="desc", platform="P1")
            for i in range(4)
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query", batch_size=2))
        # Should process in 2 batches (batch_size=2, 4 items)
        assert len(result) == 2  # Only the relevant ones

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_filter_listings_rate_limit_retry(self, mock_sleep, mock_llm_client):
        """Test filtering with rate limit retry."""
        import httpx
        # First call raises 429, second succeeds
        mock_llm_client.chat = AsyncMock(
            side_effect=[
                httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=MagicMock(status_code=429)),
                '{"results": [{"id": 0, "relevant": true, "reason": "Good"}]}'
            ]
        )
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query", max_retries=3))
        assert len(result) == 1
        assert result[0].relevant is True
        # Should have called sleep for retry
        assert mock_sleep.called

    def test_filter_listings_with_custom_batch_size(self, mock_llm_client):
        """Test filtering with custom batch size."""
        mock_response = '{"results": [{"id": 0, "relevant": true, "reason": "Good"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        filter_obj = LLMFilter(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(filter_obj.filter_listings(listings, "test query", batch_size=5))
        assert len(result) == 1
        assert result[0].relevant is True
