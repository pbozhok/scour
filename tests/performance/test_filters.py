"""
Performance tests for filter modules.

Validates that filters complete within 2 seconds per spec requirement.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from filters.keyword_filter import KeywordFilter
from models import Listing


class TestFilterPerformance:
    """Performance tests for filters."""
    
    @pytest.mark.asyncio
    async def test_keyword_filter_performance_with_100_listings(self):
        """Test KeywordFilter completes within 2 seconds with 100 listings."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        # Create 100 mock listings
        listings = []
        for i in range(100):
            listing = MagicMock()
            listing.title = f"Product {i}"
            listing.description = f"Description for product {i}"
            listings.append(listing)
        
        start_time = time.time()
        result = await filter_obj.filter(listings, "Product", {})
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"KeywordFilter took {elapsed:.2f}s (target: <2s)"
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_keyword_filter_performance_with_1000_listings(self):
        """Test KeywordFilter completes within 2 seconds with 1000 listings."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        # Create 1000 mock listings
        listings = []
        for i in range(1000):
            listing = MagicMock()
            listing.title = f"Product {i}"
            listing.description = f"Description for product {i}"
            listings.append(listing)
        
        start_time = time.time()
        result = await filter_obj.filter(listings, "Product", {})
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"KeywordFilter took {elapsed:.2f}s with 1000 listings (target: <2s)"
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_keyword_filter_execute_performance(self):
        """Test KeywordFilter.execute completes within 2 seconds."""
        from core.module import PipelineContext
        
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        # Create context with 50 listings
        listings = []
        for i in range(50):
            listing = MagicMock()
            listing.title = f"Test Product {i}"
            listing.description = "Test description"
            listings.append(listing)
        
        context = PipelineContext(query="Test", listings=listings)
        
        start_time = time.time()
        result = await filter_obj.execute(context)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"KeywordFilter.execute took {elapsed:.2f}s (target: <2s)"
        assert result is context
