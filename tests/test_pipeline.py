"""
Tests for the modular pipeline.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.pipeline import Pipeline, PipelineConfig
from core.module import PipelineContext, PipelineError, ModuleType
from core.registry import ModuleRegistry, registry as global_registry


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""
    
    def test_default_values(self):
        """Test PipelineConfig has sensible defaults."""
        config = PipelineConfig(query="test")
        assert config.query == "test"
        assert config.max_results == 20
        assert config.target_currency == "EUR"
        assert config.llm_backend == "gemini"
        assert config.skip_preprocess is False
        assert config.skip_filter is False
        assert config.skip_score is False
        assert config.skip_reviews is False
        assert config.debug is False
    
    def test_custom_values(self):
        """Test PipelineConfig accepts custom values."""
        config = PipelineConfig(
            query="iPhone 15",
            max_results=50,
            target_currency="DKK",
            llm_backend="mistral",
            skip_filter=True,
            debug=True
        )
        assert config.query == "iPhone 15"
        assert config.max_results == 50
        assert config.target_currency == "DKK"
        assert config.llm_backend == "mistral"
        assert config.skip_filter is True
        assert config.debug is True
    
    def test_to_dict(self):
        """Test PipelineConfig can be converted to dict."""
        config = PipelineConfig(
            query="test query",
            max_results=30,
            target_currency="SEK",
            debug=True
        )
        d = config.to_dict()
        assert d["query"] == "test query"
        assert d["max_results"] == 30
        assert d["target_currency"] == "SEK"
        assert d["debug"] is True


class TestPipeline:
    """Tests for Pipeline class."""
    
    def test_pipeline_initialization(self):
        """Test Pipeline can be initialized."""
        pipeline = Pipeline()
        assert pipeline is not None
        assert pipeline.registry is global_registry
    
    def test_pipeline_with_custom_registry(self):
        """Test Pipeline can use a custom registry."""
        custom_registry = ModuleRegistry()
        pipeline = Pipeline(registry=custom_registry)
        assert pipeline.registry is custom_registry
    
    def test_load_modules_empty_registry(self):
        """Test load_modules works with empty registry."""
        pipeline = Pipeline()
        pipeline._modules = {}
        pipeline.load_modules()
        # Should not raise, modules dict should be populated
        assert isinstance(pipeline._modules, dict)
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_registry(self):
        """Test execute creates a valid PipelineContext even with no modules."""
        # Create a fresh registry with no modules
        from core.registry import ModuleRegistry
        empty_registry = ModuleRegistry()
        
        pipeline = Pipeline(registry=empty_registry)
        config = PipelineConfig(query="test", max_results=10)
        
        # Ensure modules dict is empty
        pipeline._modules = {}
        
        context = await pipeline.execute(config)
        
        assert isinstance(context, PipelineContext)
        assert context.query == "test"
        assert context.config == config.to_dict()
    
    @pytest.mark.asyncio
    async def test_execute_with_skip_flags(self):
        """Test execute respects skip flags in config."""
        pipeline = Pipeline()
        config = PipelineConfig(
            query="test",
            skip_filter=True,
            skip_score=True,
            skip_reviews=True
        )
        
        pipeline._modules = {}
        context = await pipeline.execute(config)
        
        assert isinstance(context, PipelineContext)


class TestPipelineContext:
    """Tests for PipelineContext dataclass."""
    
    def test_empty_context(self):
        """Test PipelineContext can be created empty."""
        context = PipelineContext(query="test")
        assert context.query == "test"
        assert context.listings == []
        assert context.config == {}
        assert context.errors == []
        assert context.metadata == {}
    
    def test_add_listing(self):
        """Test adding a single listing."""
        context = PipelineContext(query="test")
        listing = MagicMock()
        listing.title = "Test Item"
        
        context.add_listing(listing)
        
        assert len(context.listings) == 1
        assert context.listings[0] is listing
    
    def test_add_listings(self):
        """Test adding multiple listings."""
        context = PipelineContext(query="test")
        listings = [MagicMock() for _ in range(3)]
        
        context.add_listings(listings)
        
        assert len(context.listings) == 3
    
    def test_add_error(self):
        """Test adding an error."""
        context = PipelineContext(query="test")
        
        context.add_error(
            module_name="test-module",
            error_type="TEST_ERROR",
            message="Test error message"
        )
        
        assert len(context.errors) == 1
        error = context.errors[0]
        assert isinstance(error, PipelineError)
        assert error.module_name == "test-module"
        assert error.error_type == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.severity == "ERROR"
    
    def test_get_config(self):
        """Test getting config values."""
        context = PipelineContext(
            query="test",
            config={"key1": "value1", "key2": 42}
        )
        
        assert context.get_config("key1") == "value1"
        assert context.get_config("key2") == 42
        assert context.get_config("nonexistent") is None
        assert context.get_config("nonexistent", "default") == "default"
    
    def test_set_and_get_metadata(self):
        """Test setting and getting metadata."""
        context = PipelineContext(query="test")
        
        context.set_metadata("test_key", "test_value")
        assert context.get_metadata("test_key") == "test_value"
        assert context.get_metadata("nonexistent") is None
        assert context.get_metadata("nonexistent", "default") == "default"
    
    def test_get_listings_alias(self):
        """Test get_listings returns listings."""
        context = PipelineContext(query="test")
        listings = [MagicMock(), MagicMock()]
        context.listings = listings
        
        assert context.get_listings() is listings


class TestPipelineError:
    """Tests for PipelineError dataclass."""
    
    def test_error_creation(self):
        """Test PipelineError can be created."""
        error = PipelineError(
            module_name="test-module",
            error_type="TEST_ERROR",
            message="Test message"
        )
        
        assert error.module_name == "test-module"
        assert error.error_type == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.severity == "ERROR"
        assert error.context == {}
    
    def test_error_with_custom_severity(self):
        """Test PipelineError with custom severity."""
        error = PipelineError(
            module_name="test",
            error_type="WARNING",
            message="Warning message",
            severity="WARNING"
        )
        
        assert error.severity == "WARNING"
    
    def test_error_with_context(self):
        """Test PipelineError with additional context."""
        error = PipelineError(
            module_name="test",
            error_type="ERROR",
            message="Error message",
            context={"key": "value"}
        )
        
        assert error.context == {"key": "value"}
