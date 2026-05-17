"""
Tests for reviewers.summarizer module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from models import Listing
from reviewers.summarizer import ReviewSummarizer


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat = AsyncMock()
    return mock


class TestReviewSummarizer:
    """Tests for ReviewSummarizer class."""

    def test_summarizer_initialization(self, mock_llm_client):
        """Test ReviewSummarizer initialization."""
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        assert summarizer.llm_client == mock_llm_client
        assert summarizer.debug is False
        assert hasattr(summarizer, 'searcher')

    def test_summarizer_debug_mode(self, mock_llm_client):
        """Test ReviewSummarizer with debug mode."""
        summarizer = ReviewSummarizer(mock_llm_client, debug=True)
        assert summarizer.debug is True

    def test_search_reviews_for_models_empty_list(self, mock_llm_client):
        """Test searching reviews with empty listings."""
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        result = asyncio.run(summarizer.search_reviews_for_models([]))
        assert result == {}

    def test_search_reviews_for_models_no_models(self, mock_llm_client):
        """Test searching reviews when no listings have product_model."""
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2", product_model=""),
        ]
        result = asyncio.run(summarizer.search_reviews_for_models(listings))
        assert result == {}

    def test_generate_summary_for_model_no_reviews(self, mock_llm_client):
        """Test generating summary with no reviews."""
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        result = asyncio.run(summarizer.generate_summary_for_model("iPhone 15", []))
        assert result["summary"] == "No reviews found."
        assert result["links"] == []

    def test_generate_summary_for_model_with_reviews(self, mock_llm_client):
        """Test generating summary with reviews."""
        mock_response = '{"summary": "This is a great product with excellent camera quality."}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        reviews = [
            {"title": "Review 1", "snippet": "Great camera", "url": "https://review1.com"},
            {"title": "Review 2", "snippet": "Excellent quality", "url": "https://review2.com"},
        ]
        result = asyncio.run(summarizer.generate_summary_for_model("iPhone 15", reviews))
        assert "great product" in result["summary"].lower()
        assert len(result["links"]) == 2

    def test_generate_summary_for_model_with_list_response(self, mock_llm_client):
        """Test generating summary with LLM returning a list."""
        mock_response = '{"summary": "Test summary"}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        reviews = [{"title": "Review", "snippet": "test", "url": "https://example.com"}]
        result = asyncio.run(summarizer.generate_summary_for_model("iPhone 15", reviews))
        assert result["summary"] == "Test summary"

    def test_generate_summary_for_model_with_error(self, mock_llm_client):
        """Test generating summary with LLM error."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))
        
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        reviews = [{"title": "Review", "snippet": "test", "url": "https://example.com"}]
        result = asyncio.run(summarizer.generate_summary_for_model("iPhone 15", reviews))
        assert "Error generating summary" in result["summary"]
        assert result["links"] == ["https://example.com"]

    def test_aggregate_reviews_empty_list(self, mock_llm_client):
        """Test aggregating reviews with empty listings."""
        summarizer = ReviewSummarizer(mock_llm_client, debug=False)
        # Should not raise
        result = asyncio.run(summarizer.aggregate_reviews([]))
        assert result is None
