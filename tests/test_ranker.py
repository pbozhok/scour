"""
Tests for ranker module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from models import Listing
from ranker import Ranker


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat = AsyncMock()
    return mock


class TestRanker:
    """Tests for Ranker class."""

    def test_ranker_initialization(self, mock_llm_client):
        """Test Ranker initialization."""
        ranker = Ranker(mock_llm_client, debug=False)
        assert ranker.llm_client == mock_llm_client
        assert ranker.debug is False
        assert ranker.no_score is False

    def test_ranker_debug_mode(self, mock_llm_client):
        """Test Ranker with debug mode."""
        ranker = Ranker(mock_llm_client, debug=True)
        assert ranker.debug is True

    def test_ranker_no_score_mode(self, mock_llm_client):
        """Test Ranker with no_score mode."""
        ranker = Ranker(mock_llm_client, debug=False, no_score=True)
        assert ranker.no_score is True

    def test_score_and_rank_empty_list(self, mock_llm_client):
        """Test scoring and ranking empty list."""
        ranker = Ranker(mock_llm_client, debug=False)
        result = asyncio.run(ranker.score_and_rank([], "test query"))
        assert result == []

    def test_score_and_rank_no_score_mode(self, mock_llm_client):
        """Test scoring and ranking with no_score=True (price-based sort)."""
        ranker = Ranker(mock_llm_client, debug=False, no_score=True)
        listings = [
            Listing(title="Expensive", price=500.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Cheap", price=100.0, currency="EUR", url="url2", description="desc", platform="P2"),
            Listing(title="Mid", price=300.0, currency="EUR", url="url3", description="desc", platform="P3"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        # Should be sorted by price ascending (cheapest first)
        assert result[0].title == "Cheap"
        assert result[1].title == "Mid"
        assert result[2].title == "Expensive"
        # Scores should be set based on price
        assert result[0].score > result[1].score
        assert result[1].score > result[2].score

    def test_score_and_rank_with_llm_response(self, mock_llm_client):
        """Test scoring and ranking with LLM response."""
        # Setup mock response
        mock_response = '{"scores": [{"id": 0, "score": 9.0, "reason": "Great value"}, {"id": 1, "score": 7.0, "reason": "Good"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        ranker = Ranker(mock_llm_client, debug=False)
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

    def test_score_and_rank_with_llm_error_fallback(self, mock_llm_client):
        """Test scoring and ranking with LLM error (should fallback to price sort)."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))
        
        ranker = Ranker(mock_llm_client, debug=False)
        listings = [
            Listing(title="Expensive", price=500.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Cheap", price=100.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        # Should fallback to price-based sort (cheapest first = highest score)
        assert result[0].title == "Cheap"
        assert result[1].title == "Expensive"

    def test_score_and_rank_suspicious_price_warning(self, mock_llm_client, capsys):
        """Test that suspicious prices trigger a warning."""
        mock_llm_client.chat = AsyncMock(return_value='{"scores": [{"id": 0, "score": 5.0, "reason": "ok"}]}')
        
        ranker = Ranker(mock_llm_client, debug=False)
        listings = [
            Listing(title="Suspicious", price=50000.0, currency="EUR", url="url1", description="desc", platform="P1"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        captured = capsys.readouterr()
        assert "Suspicious price" in captured.out

    def test_score_and_rank_malformed_llm_response(self, mock_llm_client):
        """Test scoring and ranking with malformed LLM response."""
        mock_llm_client.chat = AsyncMock(return_value='Not a valid JSON')
        
        ranker = Ranker(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        # Should fallback to price-based sort
        assert result[0].title == "Item 1"
        assert result[1].title == "Item 2"

    def test_score_and_rank_zero_price_handling(self, mock_llm_client):
        """Test scoring and ranking with zero price."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("Error"))
        
        ranker = Ranker(mock_llm_client, debug=False)
        listings = [
            Listing(title="Free", price=0.0, currency="EUR", url="url1", description="desc", platform="P1"),
            Listing(title="Paid", price=100.0, currency="EUR", url="url2", description="desc", platform="P2"),
        ]
        result = asyncio.run(ranker.score_and_rank(listings, "test query"))
        # Free item should come first (infall for price sort)
        assert result[0].title == "Free"
        assert result[1].title == "Paid"
