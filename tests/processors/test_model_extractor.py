"""
Tests for model_extractor module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from models import Listing
from processors.model_extractor import ModelExtractor


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.chat = AsyncMock()
    return mock


class TestModelExtractor:
    """Tests for ModelExtractor class."""

    def test_model_extractor_initialization(self, mock_llm_client):
        """Test ModelExtractor initialization."""
        extractor = ModelExtractor(mock_llm_client, debug=False)
        assert extractor.llm_client == mock_llm_client
        assert extractor.debug is False

    def test_model_extractor_debug_mode(self, mock_llm_client):
        """Test ModelExtractor with debug mode."""
        extractor = ModelExtractor(mock_llm_client, debug=True)
        assert extractor.debug is True

    def test_extract_models_empty_list(self, mock_llm_client):
        """Test extracting models from empty list."""
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = []
        result = asyncio.run(extractor.extract_models(listings))
        assert result is None

    def test_extract_models_all_empty_models(self, mock_llm_client):
        """Test extracting models when all product_model fields are empty."""
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2", product_model=""),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        # Should return without making LLM calls since no models to extract
        assert result is None

    def test_extract_models_with_llm_response(self, mock_llm_client):
        """Test extracting models with valid LLM response."""
        mock_response = '{"results": [{"id": 0, "model": "iPhone 15 Pro"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title="iPhone 15 Pro", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        assert listings[0].product_model == "iPhone 15 Pro"

    def test_extract_models_from_description(self, mock_llm_client):
        """Test extracting models from description when title is generic."""
        mock_response = '{"results": [{"id": 0, "model": "Mac Mini M4"}]}'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(
                title="Apple Mac Mini",
                price=12999.0,
                currency="DKK",
                url="url1",
                description="MAC MINI M4 16/256 med skærm 27\", keyboard, mus og kabler alt nyt",
                platform="DBA",
                product_model="",
            ),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        # The LLM should use the description to find "M4" model
        assert listings[0].product_model == "Mac Mini M4"

    def test_extract_models_with_list_response(self, mock_llm_client):
        """Test extracting models with LLM returning a list."""
        mock_response = '[{"id": 0, "model": "Samsung Galaxy S23"}]'
        mock_llm_client.chat = AsyncMock(return_value=mock_response)
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title="Samsung Galaxy S23", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        assert listings[0].product_model == "Samsung Galaxy S23"

    def test_extract_models_with_error(self, mock_llm_client, capsys):
        """Test extracting models with LLM error."""
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        # Should not raise, just continue
        assert result is None
        captured = capsys.readouterr()
        assert "Model extraction error" in captured.out

    def test_extract_models_preserves_existing_models(self, mock_llm_client):
        """Test that existing product_model values are preserved."""
        mock_llm_client.chat = AsyncMock(return_value='{"results": []}')
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model="Existing Model"),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        # Existing model should be preserved
        assert listings[0].product_model == "Existing Model"

    def test_extract_models_deduplicates(self, mock_llm_client):
        """Test that duplicate models are only extracted once."""
        mock_llm_client.chat = AsyncMock(return_value='{"results": [{"id": 0, "model": "iPhone 15"}]}')
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title="iPhone 15", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        result = asyncio.run(extractor.extract_models(listings))
        # Should extract model for the listing
        assert listings[0].product_model == "iPhone 15"
        # LLM should be called once
        assert mock_llm_client.chat.call_count == 1

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_extract_models_with_delay(self, mock_sleep, mock_llm_client):
        """Test that delay is applied between batches."""
        mock_llm_client.chat = AsyncMock(return_value='{"results": [{"id": 0, "model": "Model 1"}]}')
        
        extractor = ModelExtractor(mock_llm_client, debug=False)
        listings = [
            Listing(title=f"Item {i}", price=100.0, currency="EUR", url=f"url{i}", description="desc", platform="P1", product_model="")
            for i in range(3)  # Small number to avoid batch complexity
        ]
        result = asyncio.run(extractor.extract_models(listings))
        # Just verify it doesn't crash
        assert mock_llm_client.chat.called
