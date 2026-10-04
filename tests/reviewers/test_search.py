"""
Tests for reviewers.search module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from reviewers.search import ReviewSearcher


class TestReviewSearcher:
    """Tests for ReviewSearcher class."""

    def test_searcher_initialization(self):
        """Test ReviewSearcher initialization."""
        searcher = ReviewSearcher()
        assert hasattr(searcher, 'search_duckduckgo')
        assert hasattr(searcher, 'search_serpapi')
        assert hasattr(searcher, 'search_reviews')

    @staticmethod
    def _ddgs_returning(rows):
        """Stand in for reviewers.search.DDGS, used as a context manager."""
        ddgs = MagicMock()
        ddgs.text = MagicMock(return_value=rows)
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=ddgs)
        cm.__exit__ = MagicMock(return_value=False)
        factory = MagicMock(return_value=cm)
        factory.ddgs = ddgs
        return factory

    def test_search_duckduckgo(self):
        """Results from the DDGS library are mapped onto title/snippet/url."""
        factory = self._ddgs_returning([
            {"title": "Test Review", "body": "Great product review", "href": "https://example.com"},
        ])
        with patch("reviewers.search.DDGS", factory):
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_duckduckgo("iPhone 15"))

        assert len(results) == 1
        assert results[0]["title"] == "Test Review"
        assert results[0]["url"] == "https://example.com"
        assert results[0]["snippet"] == "Great product review"

    def test_search_duckduckgo_no_results(self):
        """Test DuckDuckGo search with no results."""
        with patch("reviewers.search.DDGS", self._ddgs_returning([])):
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_duckduckgo("iPhone 15"))

        assert results == []

    def test_search_duckduckgo_handles_none(self):
        """The library may return None rather than an empty list."""
        with patch("reviewers.search.DDGS", self._ddgs_returning(None)):
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_duckduckgo("iPhone 15"))

        assert results == []

    def test_search_duckduckgo_skips_untitled_rows(self):
        """Rows without a title are dropped."""
        factory = self._ddgs_returning([
            {"title": "Keeper", "body": "b", "href": "https://example.com"},
            {"title": "", "body": "b", "href": "https://example2.com"},
        ])
        with patch("reviewers.search.DDGS", factory):
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_duckduckgo("iPhone 15"))

        assert [r["title"] for r in results] == ["Keeper"]

    def test_search_duckduckgo_max_results(self):
        """max_results is handed to the search library."""
        factory = self._ddgs_returning([
            {"title": "Review 1", "body": "Snippet 1", "href": "https://example1.com"},
            {"title": "Review 2", "body": "Snippet 2", "href": "https://example2.com"},
        ])
        with patch("reviewers.search.DDGS", factory):
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_duckduckgo("iPhone 15", max_results=2))

        assert len(results) == 2
        assert factory.ddgs.text.call_args.kwargs["max_results"] == 2

    def test_search_duckduckgo_error(self):
        """A library failure is swallowed and yields no results."""
        cm = MagicMock()
        cm.__enter__ = MagicMock(side_effect=Exception("Network error"))
        cm.__exit__ = MagicMock(return_value=False)
        with patch("reviewers.search.DDGS", MagicMock(return_value=cm)):
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_duckduckgo("iPhone 15"))

        assert results == []

    @patch('httpx.AsyncClient')
    def test_search_serpapi(self, mock_async_client):
        """Test SerpAPI search."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "organic_results": [
                {"title": "Review 1", "snippet": "Snippet 1", "link": "https://example.com"},
                {"title": "Review 2", "snippet": "Snippet 2", "link": "https://example2.com"},
            ]
        }
        
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value = mock_client
        
        # Temporarily set SERPAPI_KEY for this test
        import config
        original_key = config.SERPAPI_KEY
        config.SERPAPI_KEY = "test_key"
        
        try:
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_serpapi("iPhone 15"))
            
            assert len(results) == 2
            assert results[0]["title"] == "Review 1"
            assert results[0]["url"] == "https://example.com"
        finally:
            config.SERPAPI_KEY = original_key

    @patch('httpx.AsyncClient')
    def test_search_serpapi_error(self, mock_async_client):
        """Test SerpAPI search with error."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("API error"))
        mock_async_client.return_value = mock_client
        
        import config
        original_key = config.SERPAPI_KEY
        config.SERPAPI_KEY = "test_key"
        
        try:
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_serpapi("iPhone 15"))
            
            assert results == []
        finally:
            config.SERPAPI_KEY = original_key

    @patch.object(ReviewSearcher, 'search_serpapi', new_callable=AsyncMock)
    @patch.object(ReviewSearcher, 'search_duckduckgo', new_callable=AsyncMock)
    def test_search_reviews_with_serpapi_key(self, mock_duckduckgo, mock_serpapi):
        """Test search_reviews routes to SerpAPI when key is available."""
        mock_serpapi.return_value = [{"title": "SerpAPI result"}]
        mock_duckduckgo.return_value = [{"title": "DuckDuckGo result"}]
        
        import config
        original_key = config.SERPAPI_KEY
        config.SERPAPI_KEY = "test_key"
        
        try:
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_reviews("iPhone 15"))
            
            assert mock_serpapi.called
            assert not mock_duckduckgo.called
            assert results == [{"title": "SerpAPI result"}]
        finally:
            config.SERPAPI_KEY = original_key

    @patch.object(ReviewSearcher, 'search_serpapi', new_callable=AsyncMock)
    @patch.object(ReviewSearcher, 'search_duckduckgo', new_callable=AsyncMock)
    def test_search_reviews_without_serpapi_key(self, mock_duckduckgo, mock_serpapi):
        """Test search_reviews routes to DuckDuckGo when no key."""
        mock_duckduckgo.return_value = [{"title": "DuckDuckGo result"}]
        
        import config
        original_key = config.SERPAPI_KEY
        config.SERPAPI_KEY = None
        
        try:
            searcher = ReviewSearcher()
            results = asyncio.run(searcher.search_reviews("iPhone 15"))
            
            assert not mock_serpapi.called
            assert mock_duckduckgo.called
            assert results == [{"title": "DuckDuckGo result"}]
        finally:
            config.SERPAPI_KEY = original_key
