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
    mock = MagicMock()
    mock.chat = AsyncMock()
    return mock


@pytest.fixture
def extractor(mock_llm_client):
    e = ModelExtractor(debug=False)
    e._llm_client = mock_llm_client
    e._initialized = True
    return e


class TestModelExtractor:

    def test_model_extractor_initialization(self, extractor, mock_llm_client):
        assert extractor._llm_client == mock_llm_client
        assert extractor.debug is False

    def test_model_extractor_debug_mode(self, mock_llm_client):
        e = ModelExtractor(debug=True)
        e._llm_client = mock_llm_client
        e._initialized = True
        assert e.debug is True

    def test_extract_models_empty_list(self, extractor):
        result = asyncio.run(extractor.process([], {}))
        assert result == []

    def test_extract_models_all_empty_models(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='{"results": []}')
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
            Listing(title="Item 2", price=200.0, currency="EUR", url="url2", description="desc", platform="P2", product_model=""),
        ]
        result = asyncio.run(extractor.process(listings, {}))
        assert result == listings
        assert listings[0].product_model == ""
        assert listings[1].product_model == ""

    def test_extract_models_with_llm_response(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='{"results": [{"id": 0, "model": "iPhone 15 Pro"}]}')
        listings = [
            Listing(title="iPhone 15 Pro", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        asyncio.run(extractor.process(listings, {}))
        assert listings[0].product_model == "iPhone 15 Pro"

    def test_extract_models_from_description(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='{"results": [{"id": 0, "model": "Mac Mini M4"}]}')
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
        asyncio.run(extractor.process(listings, {}))
        assert listings[0].product_model == "Mac Mini M4"

    def test_extract_models_with_list_response(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='[{"id": 0, "model": "Samsung Galaxy S23"}]')
        listings = [
            Listing(title="Samsung Galaxy S23", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        asyncio.run(extractor.process(listings, {}))
        assert listings[0].product_model == "Samsung Galaxy S23"

    def test_extract_models_with_error(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(side_effect=Exception("LLM Error"))
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        result = asyncio.run(extractor.process(listings, {}))
        assert result == listings
        assert listings[0].product_model == ""

    def test_extract_models_preserves_existing_models(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='{"results": []}')
        listings = [
            Listing(title="Item 1", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model="Existing Model"),
        ]
        asyncio.run(extractor.process(listings, {}))
        assert listings[0].product_model == "Existing Model"

    def test_extract_models_deduplicates(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='{"results": [{"id": 0, "model": "iPhone 15"}]}')
        listings = [
            Listing(title="iPhone 15", price=100.0, currency="EUR", url="url1", description="desc", platform="P1", product_model=""),
        ]
        asyncio.run(extractor.process(listings, {}))
        assert listings[0].product_model == "iPhone 15"
        assert mock_llm_client.chat.call_count == 1

    def test_extract_models_with_delay(self, extractor, mock_llm_client):
        mock_llm_client.chat = AsyncMock(return_value='{"results": [{"id": 0, "model": "Model 1"}]}')
        listings = [
            Listing(title=f"Item {i}", price=100.0, currency="EUR", url=f"url{i}", description="desc", platform="P1", product_model="")
            for i in range(3)
        ]
        asyncio.run(extractor.process(listings, {}))
        assert mock_llm_client.chat.called
