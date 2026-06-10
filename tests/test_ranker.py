"""
Tests for RankerModule.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from models import Listing
from rankers.ranker_module import RankerModule


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat = AsyncMock()
    return mock


@pytest.fixture
def ranker(mock_llm_client):
    """Create a RankerModule with a mock LLM client."""
    module = RankerModule()
    module._llm_client = mock_llm_client
    module._initialized = True
    return module


@pytest.fixture
def ranker_no_score():
    """Create a RankerModule in no-score (price-sort) mode."""
    module = RankerModule(no_score=True)
    module._initialized = True
    return module


class TestRankerModule:
    """Tests for RankerModule class."""

    def test_ranker_initialization(self, mock_llm_client):
        """Test RankerModule initialization."""
        module = RankerModule()
        module._llm_client = mock_llm_client
        module._initialized = True
        assert module._llm_client == mock_llm_client
        assert module.no_score is False

    def test_ranker_no_score_mode(self):
        """Test RankerModule with no_score mode."""
        module = RankerModule(no_score=True)
        assert module.no_score is True

    def test_score_and_rank_empty_list(self, ranker):
        """Test scoring and ranking empty list."""
        result = asyncio.run(ranker.score_and_rank([], "test query"))
        assert result == []

    def test_score_and_rank_no_score_mode(self, ranker_no_score):
        """Test scoring and ranking with no_score=True (price-based sort)."""
        listings = [
            Listing(title="Expensive", price=500.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Cheap", price=100.0, currency="EUR", url="url2", description="desc", platform="P2"),
            Listing(title="Mid", price=300.0, currency="EUR", url="url3", description="desc", platform="P3"),
        ]
        result = asyncio.run(ranker_no_score.score_and_rank(listings, "test query"))
        # Should be sorted by price ascending (cheapest first)
        assert result[0].title == "Cheap"
        assert result[1].title == "Mid"
        assert result[2].title == "Expensive"
        # Scores should be set based on price
        assert result[0].score > result[1].score
        assert result[1].score > result[2].score

    def test_score_and_rank_with_llm_response(self, ranker, mock_llm_client):
        """Test scoring and ranking with LLM response."""
        mock_response = '{"scores": [{"id": 0, "score": 9.0, "reason": "Great value"}, {"id": 1, "score": 7.0, "reason": "Good"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)

        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc1", platform="P1"),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc2", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        # Should be sorted by score descending (highest first)
        assert result[0].title == "Item 1"
        assert result[1].title == "Item 2"
        assert result[0].score == 9.0
        assert result[1].score == 7.0

    def test_score_and_rank_with_llm_error_fallback(self, ranker, mock_llm_client):
        """Test scoring and ranking with LLM error falls back to price sort."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))

        listings = [
            Listing(title="Expensive", price=500.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Cheap", price=100.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        # Should fallback to price-based sort (cheapest = highest score)
        assert result[0].title == "Cheap"
        assert result[1].title == "Expensive"

    def test_score_and_rank_suspicious_price_warning(self, ranker, mock_llm_client, capsys):
        """Test that suspicious prices trigger a warning."""
        mock_llm_client.chat = AsyncMock(return_value='{"scores": [{"id": 0, "score": 5.0, "reason": "ok"}]}')

        listings = [
            Listing(title="Suspicious", price=50000.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        asyncio.run(ranker.score_and_rank(listings, "test query"))
        captured = capsys.readouterr()
        assert "Suspicious price" in captured.out

    def test_score_and_rank_malformed_llm_response(self, ranker, mock_llm_client):
        """Test scoring and ranking with malformed LLM response falls back to price sort."""
        mock_llm_client.chat = AsyncMock(return_value='Not a valid JSON')

        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        assert result[0].title == "Item 1"
        assert result[1].title == "Item 2"

    def test_score_and_rank_zero_price_handling(self, ranker, mock_llm_client):
        """Test scoring and ranking with zero price in fallback mode."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("Error"))

        listings = [
            Listing(title="Free", price=0.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Paid", price=100.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        assert result[0].title == "Free"
        assert result[1].title == "Paid"
