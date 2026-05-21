"""
Performance tests for scraper modules.

Validates that scrapers complete within 5 seconds per spec requirement.
These tests use mocking to avoid real network calls.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from scrapers.dba import DBAScraper
from scrapers.tradera import TraderaScraper
from models import Listing


class TestScraperPerformance:
    """Performance tests for scrapers."""
    
    @pytest.mark.asyncio
    async def test_dba_scraper_initialization_performance(self):
        """Test DBA scraper initialization is fast."""
        start_time = time.time()
        scraper = DBAScraper(debug=False)
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1, f"DBA scraper init took {elapsed:.4f}s (target: <0.1s)"
    
    @pytest.mark.asyncio
    async def test_tradera_scraper_initialization_performance(self):
        """Test Tradera scraper initialization is fast."""
        start_time = time.time()
        scraper = TraderaScraper(debug=False)
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1, f"Tradera scraper init took {elapsed:.4f}s (target: <0.1s)"
    
    @pytest.mark.asyncio
    async def test_dba_scraper_performance_with_mock(self):
        """Test DBA scraper completes quickly with mocked HTTP."""
        scraper = DBAScraper(debug=False)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = '<html></html>'
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            start_time = time.time()
            listings = await scraper.scrape("test query", max_results=10)
            elapsed = time.time() - start_time
            
            assert elapsed < 1.0, f"DBA scraper took {elapsed:.2f}s (target: <5s)"
    
    @pytest.mark.asyncio
    async def test_tradera_scraper_performance_with_mock(self):
        """Test Tradera scraper completes quickly with mocked HTTP."""
        scraper = TraderaScraper(debug=False)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.text = '<html></html>'
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            start_time = time.time()
            listings = await scraper.scrape("test query", max_results=10)
            elapsed = time.time() - start_time
            
            assert elapsed < 1.0, f"Tradera scraper took {elapsed:.2f}s (target: <5s)"
    
    @pytest.mark.asyncio
    async def test_scrapers_module_type_check_performance(self):
        """Test that module type checking is fast."""
        from core.module import ModuleType
        
        start_time = time.time()
        for _ in range(1000):
            _ = ModuleType.SCRAPER
            _ = ModuleType.FILTER
            _ = ModuleType.PROCESSOR
            _ = ModuleType.REVIEWER
            _ = ModuleType.LLM
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1, f"Module type checks took {elapsed:.4f}s (target: <0.1s)"
