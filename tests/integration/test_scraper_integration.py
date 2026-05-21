"""
Integration tests for scraper modules.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from core.module import ModuleType, PipelineContext, PipelineError
from scrapers.base import BaseScraper
from scrapers.dba import DBAScraper
from scrapers.vinted import VintedScraper
from scrapers.tradera import TraderaScraper


# ============================================================================
# Integration Tests (T024 [P] [US1])
# ============================================================================

class TestScraperPipelineIntegration:
    """Integration tests for scrapers in the pipeline context."""
    
    @pytest.mark.asyncio
    async def test_scraper_pipeline_integration(self):
        """Scrapers must integrate correctly with PipelineContext."""
        # Create a pipeline context
        context = PipelineContext(
            query="iPhone 15",
            listings=[],
            config={"max_results": 5, "timeout": 30},
            errors=[],
            metadata={}
        )
        
        # Create scraper
        scraper = DBAScraper(debug=False)
        
        # Mock the scrape method
        mock_listing = Mock()
        mock_listing.id = "123"
        mock_listing.title = "Test iPhone"
        mock_listing.price = 500.0
        mock_listing.currency = "EUR"
        mock_listing.url = "https://example.com/123"
        mock_listing.platform = "DBA"
        
        with patch.object(scraper, 'scrape', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = [mock_listing]
            
            result = await scraper.execute(context)
            
            # Verify results
            assert result is not None
            assert isinstance(result, PipelineContext)
            assert result.query == "iPhone 15"
            assert len(result.listings) == 1
            assert result.listings[0].id == "123"
            assert result.metadata.get("dba-scraper_count") == 1
    
    @pytest.mark.asyncio
    async def test_multiple_scrapers_in_pipeline(self):
        """Multiple scrapers must work together in a pipeline."""
        context = PipelineContext(
            query="test",
            listings=[],
            config={"max_results": 3},
            errors=[],
            metadata={}
        )
        
        scrapers = [
            DBAScraper(debug=False),
            VintedScraper(debug=False),
            TraderaScraper(debug=False),
        ]
        
        # Mock each scraper to return different listings
        mock_listings = [
            [Mock(id="dba-1", title="DBA Item", platform="DBA")],
            [Mock(id="vinted-1", title="Vinted Item", platform="Vinted")],
            [Mock(id="tradera-1", title="Tradera Item", platform="Tradera")],
        ]
        
        for scraper, listings in zip(scrapers, mock_listings):
            with patch.object(scraper, 'scrape', new_callable=AsyncMock) as mock_scrape:
                mock_scrape.return_value = listings
                result = await scraper.execute(context)
                context = result
        
        # All scrapers should have added their listings
        assert len(context.listings) >= 3
        platforms = {listing.platform for listing in context.listings}
        assert "DBA" in platforms
        assert "Vinted" in platforms
        assert "Tradera" in platforms
    
    @pytest.mark.asyncio
    async def test_scraper_error_isolation(self):
        """Scraper errors must be isolated and not crash the pipeline."""
        context = PipelineContext(
            query="test",
            listings=[],
            config={},
            errors=[],
            metadata={}
        )
        
        scrapers = [
            DBAScraper(debug=False),
            VintedScraper(debug=False),
        ]
        
        # First scraper works
        with patch.object(scrapers[0], 'scrape', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = [Mock(id="1", title="Working")]
            context = await scrapers[0].execute(context)
        
        # Second scraper fails
        with patch.object(scrapers[1], 'scrape', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Network error")
            context = await scrapers[1].execute(context)
        
        # Should have one listing from first scraper
        assert len(context.listings) == 1
        # Should have one error from second scraper
        assert len(context.errors) == 1
        assert context.errors[0].module_name == "vinted-scraper"
        assert context.errors[0].error_type == "SCRAPE_ERROR"
    
    @pytest.mark.asyncio
    async def test_scraper_with_module_name(self):
        """Scrapers must have correct module names for error reporting."""
        scrapers = [
            (DBAScraper(debug=False), "dba-scraper"),
            (VintedScraper(debug=False), "vinted-scraper"),
            (TraderaScraper(debug=False), "tradera-scraper"),
        ]
        
        for scraper, expected_name in scrapers:
            assert scraper.name == expected_name
            assert scraper.module_type == ModuleType.SCRAPER


# ============================================================================
# Mock Scraper Test (T024 [P] [US1])
# ============================================================================

class TestMockScraper:
    """Tests for adding a new mock scraper module."""
    
    @pytest.mark.asyncio
    async def test_mock_scraper_creation(self):
        """A new mock scraper must be easily creatable."""
        # Create a mock scraper by extending BaseScraper
        class MockScraper(BaseScraper):
            name = "mock-scraper"
            module_type = ModuleType.SCRAPER
            version = "1.0.0"
            platform = "MockPlatform"
            
            async def scrape(self, query, max_results=20):
                return [
                    Mock(id="mock-1", title="Mock Item", price=100.0, 
                         currency="EUR", url="https://mock.com/1", platform="MockPlatform")
                ]
        
        scraper = MockScraper(debug=False)
        assert scraper.name == "mock-scraper"
        assert scraper.module_type == ModuleType.SCRAPER
        assert scraper.version == "1.0.0"
        assert scraper.platform == "MockPlatform"
    
    @pytest.mark.asyncio
    async def test_mock_scraper_execute(self):
        """Mock scraper must execute correctly in pipeline."""
        class MockScraper(BaseScraper):
            name = "mock-scraper"
            module_type = ModuleType.SCRAPER
            version = "1.0.0"
            platform = "MockPlatform"
            
            async def scrape(self, query, max_results=20):
                return [
                    Mock(id="mock-1", title="Mock Item", price=100.0,
                         currency="EUR", url="https://mock.com/1", platform="MockPlatform")
                ]
        
        scraper = MockScraper(debug=False)
        context = PipelineContext(
            query="test",
            listings=[],
            config={},
            errors=[],
            metadata={}
        )
        
        result = await scraper.execute(context)
        
        assert len(result.listings) == 1
        assert result.listings[0].id == "mock-1"
        assert result.metadata.get("mock-scraper_count") == 1
    
    def test_mock_scraper_has_all_required_attributes(self):
        """Mock scraper must have all required Module attributes."""
        class MockScraper(BaseScraper):
            name = "mock-scraper"
            module_type = ModuleType.SCRAPER
            version = "1.0.0"
            platform = "MockPlatform"
            
            async def scrape(self, query, max_results=20):
                return []
        
        # Check it has all required methods from Module
        assert hasattr(MockScraper, 'initialize')
        assert hasattr(MockScraper, 'validate')
        assert hasattr(MockScraper, 'execute')
        assert hasattr(MockScraper, 'cleanup')
        assert hasattr(MockScraper, 'scrape')
        
        # Check class attributes
        assert hasattr(MockScraper, 'name')
        assert hasattr(MockScraper, 'module_type')
        assert hasattr(MockScraper, 'version')
        assert hasattr(MockScraper, 'platform')
