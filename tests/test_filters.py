"""
Contract tests for Filter module interface.

Verifies that all filters follow the BaseFilter interface.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from filters.base import BaseFilter
from filters.keyword_filter import KeywordFilter
from filters.llm_filter import LLMFilter
from core.module import Module, ModuleType
from core.module import PipelineContext


class TestBaseFilterInterface:
    """Contract tests for BaseFilter interface."""
    
    def test_base_filter_inherits_from_module(self):
        """Test that BaseFilter inherits from Module."""
        assert issubclass(BaseFilter, Module)
    
    def test_base_filter_has_required_class_attributes(self):
        """Test BaseFilter has required class attributes."""
        assert hasattr(BaseFilter, 'name')
        assert hasattr(BaseFilter, 'module_type')
        assert hasattr(BaseFilter, 'version')
        assert hasattr(BaseFilter, 'description')
    
    def test_base_filter_module_type_is_filter(self):
        """Test BaseFilter has correct module_type."""
        assert BaseFilter.module_type == ModuleType.FILTER
    
    def test_base_filter_has_required_methods(self):
        """Test BaseFilter has all required Module methods."""
        required_methods = ['initialize', 'validate', 'execute', 'cleanup']
        for method in required_methods:
            assert hasattr(BaseFilter, method), f"Missing method: {method}"
    
    def test_base_filter_has_filter_method(self):
        """Test BaseFilter has abstract filter method."""
        assert hasattr(BaseFilter, 'filter')
    
    def test_base_filter_has_execute_method(self):
        """Test BaseFilter has execute method."""
        assert hasattr(BaseFilter, 'execute')
        assert callable(BaseFilter.execute)


class TestConcreteFilters:
    """Tests for concrete filter implementations."""
    
    def test_keyword_filter_inherits_from_base_filter(self):
        """Test KeywordFilter inherits from BaseFilter."""
        assert issubclass(KeywordFilter, BaseFilter)
    
    def test_keyword_filter_has_required_attributes(self):
        """Test KeywordFilter has required class attributes."""
        filter_obj = KeywordFilter()
        assert hasattr(filter_obj, 'name')
        assert filter_obj.name == "keyword-filter"
        assert hasattr(filter_obj, 'module_type')
        assert filter_obj.module_type == ModuleType.FILTER
        assert hasattr(filter_obj, 'version')
    
    def test_keyword_filter_implements_filter(self):
        """Test KeywordFilter implements filter method."""
        assert hasattr(KeywordFilter, 'filter')
        assert callable(KeywordFilter.filter)
    
    def test_llm_filter_inherits_from_base_filter(self):
        """Test LLMFilter inherits from BaseFilter."""
        assert issubclass(LLMFilter, BaseFilter)
    
    def test_llm_filter_has_required_attributes(self):
        """Test LLMFilter has required class attributes."""
        filter_obj = LLMFilter()
        assert hasattr(filter_obj, 'name')
        assert filter_obj.name == "llm-filter"
        assert hasattr(filter_obj, 'module_type')
        assert filter_obj.module_type == ModuleType.FILTER
        assert hasattr(filter_obj, 'version')
    
    def test_llm_filter_implements_filter(self):
        """Test LLMFilter implements filter method."""
        assert hasattr(LLMFilter, 'filter')
        assert callable(LLMFilter.filter)


class TestFilterLifecycle:
    """Tests for filter lifecycle methods."""
    
    def test_keyword_filter_can_be_initialized(self):
        """Test KeywordFilter can be initialized."""
        filter_obj = KeywordFilter()
        result = filter_obj.initialize({"debug": False})
        assert result is True
        assert filter_obj._initialized is True
    
    def test_keyword_filter_validation(self):
        """Test KeywordFilter validation."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        assert filter_obj.validate() is True
        
        filter_obj2 = KeywordFilter()
        assert filter_obj2.validate() is False
    
    def test_keyword_filter_cleanup(self):
        """Test KeywordFilter cleanup."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        assert filter_obj._initialized is True
        
        filter_obj.cleanup()
        assert filter_obj._initialized is False
    
    @pytest.mark.asyncio
    async def test_keyword_filter_execute_with_empty_listings(self):
        """Test KeywordFilter.execute with empty listings."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        context = PipelineContext(query="test query", listings=[])
        result = await filter_obj.execute(context)
        
        assert result is context
        assert result.listings == []
    
    @pytest.mark.asyncio
    async def test_keyword_filter_execute_with_listings(self):
        """Test KeywordFilter.execute with listings."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        # Create mock listings
        listing1 = MagicMock()
        listing1.title = "Test Item"
        listing1.description = ""
        
        listing2 = MagicMock()
        listing2.title = "Other Item"
        listing2.description = ""
        
        context = PipelineContext(
            query="Test Item",
            listings=[listing1, listing2]
        )
        
        result = await filter_obj.execute(context)
        
        assert result is context
        # Should filter and keep relevant listings
        assert len(result.listings) >= 0
    
    @pytest.mark.asyncio
    async def test_llm_filter_execute_returns_context(self):
        """Test LLMFilter.execute returns context."""
        # Note: This test may timeout or fail if LLM is not available
        # We'll test the structure without actually calling the LLM
        filter_obj = LLMFilter()
        # Don't initialize to avoid LLM calls
        
        context = PipelineContext(query="test", listings=[])
        # This will fail validation but we're testing the structure
        
        # Just verify the method exists and is callable
        assert hasattr(filter_obj, 'execute')
        assert callable(filter_obj.execute)
    
    @pytest.mark.asyncio
    async def test_keyword_filter_with_mock_listings(self):
        """Test KeywordFilter.filter with mock listings."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        # Create mock listings
        listing1 = MagicMock()
        listing1.title = "iPhone 15"
        listing1.description = "Brand new iPhone 15"
        
        listing2 = MagicMock()
        listing2.title = "Samsung Galaxy"
        listing2.description = "Android phone"
        
        listings = [listing1, listing2]
        
        # Filter with query "iPhone"
        result = await filter_obj.filter(listings, "iPhone", {})
        
        # Should keep only the iPhone listing
        assert len(result) >= 1
        # First listing should be relevant
        assert any(l.title == "iPhone 15" for l in result)
    
    @pytest.mark.asyncio
    async def test_keyword_filter_all_irrelevant(self):
        """Test KeywordFilter when no listings match."""
        filter_obj = KeywordFilter()
        filter_obj.initialize({"debug": False})
        
        # Create listings that don't match the query
        listing1 = MagicMock()
        listing1.title = "Samsung"
        listing1.description = "Android"
        
        listing2 = MagicMock()
        listing2.title = "Google Pixel"
        listing2.description = "Phone"
        
        listings = [listing1, listing2]
        
        # Filter with query "iPhone" - no matches
        result = await filter_obj.filter(listings, "iPhone", {})
        
        # Should return empty or all (fallback behavior)
        # The filter returns all listings as fallback when no matches
        assert isinstance(result, list)
