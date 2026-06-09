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


@pytest.fixture
def llm_filter(mock_llm_client):
    """Create an initialized LLMFilter with a mock LLM client."""
    f = LLMFilter()
    f._llm_client = mock_llm_client
    f._initialized = True
    return f


class TestLLMFilter:
    """Tests for LLMFilter class."""

    def test_llm_filter_defaults(self):
        """Test LLMFilter default values."""
        f = LLMFilter()
        assert f.llm_backend == "gemini"
        assert f.debug is False

    def test_llm_filter_debug_mode(self):
        """Test LLMFilter with debug mode."""
        f = LLMFilter(debug=True)
        assert f.debug is True

    def test_filter_empty_list(self, llm_filter):
        """Test filtering empty list returns empty list."""
        result = asyncio.run(llm_filter.filter([], "test query", {}))
        assert result == []

    def test_filter_all_irrelevant_fallback(self, llm_filter, mock_llm_client):
        """Test fallback when all listings are marked irrelevant by LLM."""
        mock_llm_client.chat = AsyncMock(
            return_value='{"results": [{"id": 0, "relevant": false, "reason": "Not relevant"}]}'
        )
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(llm_filter.filter(listings, "test query", {}))
        # Should fallback to marking all as relevant
        assert len(result) == 1
        assert result[0].relevant is True
        assert "Fallback" in result[0].relevance_reason

    def test_filter_with_relevant_response(self, llm_filter, mock_llm_client):
        """Test filtering with a valid LLM response marking item as relevant."""
        mock_llm_client.chat = AsyncMock(
            return_value='{"results": [{"id": 0, "relevant": true, "reason": "Matches query well"}]}'
        )
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(llm_filter.filter(listings, "test query", {}))
        assert len(result) == 1
        assert result[0].relevant is True
        assert result[0].relevance_reason == "Matches query well"

    def test_filter_with_list_response(self, llm_filter, mock_llm_client):
        """Test filtering when LLM returns a list instead of dict."""
        mock_llm_client.chat = AsyncMock(
            return_value='[{"id": 0, "relevant": true, "reason": "Good match"}]'
        )
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(llm_filter.filter(listings, "test query", {}))
        assert len(result) == 1
        assert result[0].relevant is True

    def test_filter_with_error_keeps_all(self, llm_filter, mock_llm_client):
        """Test filtering with LLM error marks all listings as relevant."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(llm_filter.filter(listings, "test query", {"max_retries": 1}))
        assert len(result) == 2
        assert all(l.relevant for l in result)

    def test_filter_multiple_batches(self, llm_filter, mock_llm_client):
        """Test filtering processes multiple batches."""
        mock_llm_client.chat = AsyncMock(
            return_value='{"results": [{"id": 0, "relevant": true, "reason": "Good"}, {"id": 1, "relevant": false, "reason": "Bad"}]}'
        )
        listings = [
            Listing(title=f"Item {i}", price=100.0, currency="EUR", url=f"url{i}", description="desc", platform="P1")
            for i in range(4)
        ]
        result = asyncio.run(llm_filter.filter(listings, "test query", {"batch_size": 2}))
        assert len(result) == 2  # One relevant per batch

    def test_filter_custom_batch_size(self, llm_filter, mock_llm_client):
        """Test filtering respects custom batch_size from context."""
        mock_llm_client.chat = AsyncMock(
            return_value='{"results": [{"id": 0, "relevant": true, "reason": "Good"}]}'
        )
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(llm_filter.filter(listings, "test query", {"batch_size": 5}))
        assert len(result) == 1
        assert result[0].relevant is True
