"""
Contract tests for Processor module interface.

Verifies that all processors follow the BaseProcessor interface.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from processors.base import BaseProcessor
from processors.price_converter import PriceConverter
from processors.model_extractor import ModelExtractor
from processors.description_fetcher import DescriptionFetcher
from core.module import Module, ModuleType
from core.module import PipelineContext
from models import Listing


class TestBaseProcessorInterface:
    """Contract tests for BaseProcessor interface."""
    
    def test_base_processor_inherits_from_module(self):
        """Test that BaseProcessor inherits from Module."""
        assert issubclass(BaseProcessor, Module)
    
    def test_base_processor_has_required_class_attributes(self):
        """Test BaseProcessor has required class attributes."""
        assert hasattr(BaseProcessor, 'name')
        assert hasattr(BaseProcessor, 'module_type')
        assert hasattr(BaseProcessor, 'version')
        assert hasattr(BaseProcessor, 'description')
    
    def test_base_processor_module_type_is_processor(self):
        """Test BaseProcessor has correct module_type."""
        assert BaseProcessor.module_type == ModuleType.PROCESSOR
    
    def test_base_processor_has_required_methods(self):
        """Test BaseProcessor has all required Module methods."""
        required_methods = ['initialize', 'validate', 'execute', 'cleanup']
        for method in required_methods:
            assert hasattr(BaseProcessor, method), f"Missing method: {method}"
    
    def test_base_processor_has_process_method(self):
        """Test BaseProcessor has abstract process method."""
        assert hasattr(BaseProcessor, 'process')
    
    def test_base_processor_has_execute_method(self):
        """Test BaseProcessor has execute method."""
        assert hasattr(BaseProcessor, 'execute')
        assert callable(BaseProcessor.execute)


class TestConcreteProcessors:
    """Tests for concrete processor implementations."""
    
    def test_price_converter_inherits_from_base_processor(self):
        """Test PriceConverter inherits from BaseProcessor."""
        assert issubclass(PriceConverter, BaseProcessor)
    
    def test_price_converter_has_required_attributes(self):
        """Test PriceConverter has required class attributes."""
        processor = PriceConverter()
        assert hasattr(processor, 'name')
        assert processor.name == "price-converter"
        assert hasattr(processor, 'module_type')
        assert processor.module_type == ModuleType.PROCESSOR
        assert hasattr(processor, 'version')
    
    def test_price_converter_implements_process(self):
        """Test PriceConverter implements process method."""
        assert hasattr(PriceConverter, 'process')
        assert callable(PriceConverter.process)
    
    def test_model_extractor_inherits_from_base_processor(self):
        """Test ModelExtractor inherits from BaseProcessor."""
        assert issubclass(ModelExtractor, BaseProcessor)
    
    def test_model_extractor_has_required_attributes(self):
        """Test ModelExtractor has required class attributes."""
        processor = ModelExtractor()
        assert hasattr(processor, 'name')
        assert processor.name == "model-extractor"
        assert hasattr(processor, 'module_type')
        assert processor.module_type == ModuleType.PROCESSOR
        assert hasattr(processor, 'version')
    
    def test_model_extractor_implements_process(self):
        """Test ModelExtractor implements process method."""
        assert hasattr(ModelExtractor, 'process')
        assert callable(ModelExtractor.process)
    
    def test_description_fetcher_inherits_from_base_processor(self):
        """Test DescriptionFetcher inherits from BaseProcessor."""
        assert issubclass(DescriptionFetcher, BaseProcessor)
    
    def test_description_fetcher_has_required_attributes(self):
        """Test DescriptionFetcher has required class attributes."""
        processor = DescriptionFetcher()
        assert hasattr(processor, 'name')
        assert processor.name == "description-fetcher"
        assert hasattr(processor, 'module_type')
        assert processor.module_type == ModuleType.PROCESSOR
        assert hasattr(processor, 'version')
    
    def test_description_fetcher_implements_process(self):
        """Test DescriptionFetcher implements process method."""
        assert hasattr(DescriptionFetcher, 'process')
        assert callable(DescriptionFetcher.process)


class TestProcessorLifecycle:
    """Tests for processor lifecycle methods."""
    
    def test_price_converter_can_be_initialized(self):
        """Test PriceConverter can be initialized."""
        processor = PriceConverter()
        result = processor.initialize({"target_currency": "EUR", "debug": False})
        assert result is True
        assert processor._initialized is True
    
    def test_price_converter_validation(self):
        """Test PriceConverter validation."""
        processor = PriceConverter()
        processor.initialize({"target_currency": "EUR", "debug": False})
        assert processor.validate() is True
        
        processor2 = PriceConverter()
        assert processor2.validate() is False
    
    def test_price_converter_cleanup(self):
        """Test PriceConverter cleanup."""
        processor = PriceConverter()
        processor.initialize({"target_currency": "EUR", "debug": False})
        assert processor._initialized is True
        
        processor.cleanup()
        assert processor._initialized is False
    
    @pytest.mark.asyncio
    async def test_price_converter_execute_with_empty_listings(self):
        """Test PriceConverter.execute with empty listings."""
        processor = PriceConverter()
        processor.initialize({"target_currency": "EUR", "debug": False})
        
        context = PipelineContext(query="test", listings=[])
        result = await processor.execute(context)
        
        assert result is context
        assert result.listings == []
    
    @pytest.mark.asyncio
    async def test_price_converter_execute_with_listings(self):
        """Test PriceConverter.execute with listings needing conversion."""
        processor = PriceConverter()
        processor.initialize({"target_currency": "EUR", "debug": False})
        
        # Create a listing with DKK that needs conversion to EUR
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="DKK",
            url="http://test.com",
            description="",
            platform="Test"
        )
        
        context = PipelineContext(
            query="test",
            listings=[listing],
            config={"target_currency": "EUR"}
        )
        
        result = await processor.execute(context)
        
        assert result is context
        assert len(result.listings) == 1
        # Price should be converted from DKK to EUR
        # 100 DKK / 7.45 ≈ 13.42 EUR
        assert result.listings[0].currency == "EUR"
        assert result.listings[0].price > 0
    
    @pytest.mark.asyncio
    async def test_description_fetcher_execute_with_empty_listings(self):
        """Test DescriptionFetcher.execute with empty listings."""
        processor = DescriptionFetcher()
        processor.initialize({"debug": False})
        
        context = PipelineContext(query="test", listings=[])
        result = await processor.execute(context)
        
        assert result is context
        assert result.listings == []
    
    @pytest.mark.asyncio
    async def test_description_fetcher_execute_returns_context(self):
        """Test DescriptionFetcher.execute returns context."""
        processor = DescriptionFetcher()
        processor.initialize({"debug": False})
        
        # Create a listing - description fetcher won't modify it much without network
        listing = Listing(
            title="Test Item",
            price=100.0,
            currency="EUR",
            url="http://test.com",
            description="",
            platform="Test"
        )
        
        context = PipelineContext(query="test", listings=[listing])
        result = await processor.execute(context)
        
        assert result is context
        assert len(result.listings) == 1
