"""
Tests for scraper modules - Contract tests and unit tests.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from core.module import Module, ModuleType, PipelineContext, PipelineError
from scrapers.base import BaseScraper
from scrapers.dba import DBAScraper
from scrapers.vinted import VintedScraper
from scrapers.tradera import TraderaScraper


# ============================================================================
# Contract Tests: BaseScraper Interface (T022 [P] [US1])
# ============================================================================

class TestBaseScraperContract:
    """Contract tests for BaseScraper interface."""
    
    def test_base_scraper_inherits_from_module(self):
        """BaseScraper must inherit from Module."""
        assert issubclass(BaseScraper, Module)
    
    def test_base_scraper_has_required_class_attributes(self):
        """BaseScraper must have name, module_type, version class attributes."""
        assert hasattr(BaseScraper, 'name')
        assert hasattr(BaseScraper, 'module_type')
        assert hasattr(BaseScraper, 'version')
        assert hasattr(BaseScraper, 'platform')
    
    def test_base_scraper_has_required_methods(self):
        """BaseScraper must have all required Module methods."""
        assert hasattr(BaseScraper, 'initialize')
        assert hasattr(BaseScraper, 'validate')
        assert hasattr(BaseScraper, 'execute')
        assert hasattr(BaseScraper, 'cleanup')
    
    def test_base_scraper_has_scrape_method(self):
        """BaseScraper must have scrape() abstract method."""
        assert hasattr(BaseScraper, 'scrape')
        # Check it's abstract
        import inspect
        assert inspect.iscoroutinefunction(BaseScraper.scrape)
    
    def test_base_scraper_module_type_is_scraper(self):
        """BaseScraper.module_type must be SCRAPER."""
        assert BaseScraper.module_type == ModuleType.SCRAPER


# ============================================================================
# Contract Tests: Concrete Scrapers (T022 [P] [US1])
# ============================================================================

class TestConcreteScrapersContract:
    """Contract tests for concrete scraper implementations."""
    
    def test_dba_scraper_inherits_from_base_scraper(self):
        """DBAScraper must inherit from BaseScraper."""
        assert issubclass(DBAScraper, BaseScraper)
    
    def test_dba_scraper_has_required_attributes(self):
        """DBAScraper must have name, module_type, version, platform."""
        assert hasattr(DBAScraper, 'name')
        assert hasattr(DBAScraper, 'module_type')
        assert hasattr(DBAScraper, 'version')
        assert hasattr(DBAScraper, 'platform')
        assert DBAScraper.name == "dba-scraper"
        assert DBAScraper.module_type == ModuleType.SCRAPER
        assert DBAScraper.version == "1.0.0"
        assert DBAScraper.platform == "DBA"
    
    def test_vinted_scraper_inherits_from_base_scraper(self):
        """VintedScraper must inherit from BaseScraper."""
        assert issubclass(VintedScraper, BaseScraper)
    
    def test_vinted_scraper_has_required_attributes(self):
        """VintedScraper must have name, module_type, version, platform."""
        assert VintedScraper.name == "vinted-scraper"
        assert VintedScraper.module_type == ModuleType.SCRAPER
        assert VintedScraper.version == "1.0.0"
        assert VintedScraper.platform == "Vinted"
    
    def test_tradera_scraper_inherits_from_base_scraper(self):
        """TraderaScraper must inherit from BaseScraper."""
        assert issubclass(TraderaScraper, BaseScraper)
    
    def test_tradera_scraper_has_required_attributes(self):
        """TraderaScraper must have name, module_type, version, platform."""
        assert TraderaScraper.name == "tradera-scraper"
        assert TraderaScraper.module_type == ModuleType.SCRAPER
        assert TraderaScraper.version == "1.0.0"
        assert TraderaScraper.platform == "Tradera"
    
    def test_scrapers_implement_scrape_method(self):
        """All concrete scrapers must implement scrape() method."""
        import inspect
        assert inspect.iscoroutinefunction(DBAScraper.scrape)
        assert inspect.iscoroutinefunction(VintedScraper.scrape)
        assert inspect.iscoroutinefunction(TraderaScraper.scrape)


# ============================================================================
# Module Discovery Tests (T023 [P] [US1])
# ============================================================================

class TestModuleDiscovery:
    """Tests for module discovery and registration."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        from core.registry import ModuleRegistry
        return ModuleRegistry()
    
    def test_registry_can_register_scraper(self, registry):
        """Registry must be able to register a scraper module."""
        scraper = DBAScraper(debug=False)
        registry.register(scraper)
        assert registry.get_module("dba-scraper") is scraper
    
    def test_registry_gets_modules_by_type(self, registry):
        """Registry must return modules filtered by type."""
        scraper1 = DBAScraper(debug=False)
        scraper2 = VintedScraper(debug=False)
        registry.register(scraper1)
        registry.register(scraper2)
        
        scrapers = registry.get_modules(ModuleType.SCRAPER)
        assert len(scrapers) == 2
        assert all(s.module_type == ModuleType.SCRAPER for s in scrapers)
    
    def test_registry_rejects_duplicate_names(self, registry):
        """Registry must reject duplicate module names."""
        scraper1 = DBAScraper(debug=False)
        scraper2 = DBAScraper(debug=False)
        registry.register(scraper1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(scraper2)
    
    def test_registry_unregister(self, registry):
        """Registry must support unregistering modules."""
        scraper = DBAScraper(debug=False)
        registry.register(scraper)
        assert registry.get_module("dba-scraper") is scraper
        
        registry.unregister("dba-scraper")
        assert registry.get_module("dba-scraper") is None
    
    def test_module_validation(self, registry):
        """Registry must validate all registered modules."""
        scraper = DBAScraper(debug=False)
        scraper.initialize({})  # Initialize before validation
        registry.register(scraper)
        
        errors = registry.validate_all()
        # Module should be valid after initialization
        assert len(errors) == 0


# ============================================================================
# Unit Tests: Scraper Initialization and Validation (T027 [P] [US1])
# ============================================================================

class TestScraperLifecycle:
    """Unit tests for scraper lifecycle methods."""
    
    def test_scraper_can_be_initialized(self):
        """Scrapers must be initializable with config."""
        scraper = DBAScraper(debug=False)
        result = scraper.initialize({"timeout": 30})
        assert result is True
    
    def test_scraper_validation(self):
        """Scrapers must pass validation after initialization."""
        scraper = DBAScraper(debug=False)
        scraper.initialize({})
        assert scraper.validate() is True
    
    def test_scraper_cleanup(self):
        """Scrapers must support cleanup."""
        scraper = DBAScraper(debug=False)
        scraper.initialize({})
        # Cleanup should be idempotent
        scraper.cleanup()
        scraper.cleanup()  # Should not raise


# ============================================================================
# Integration Tests (T024 [P] [US1])
# ============================================================================

class TestScraperIntegration:
    """Integration tests for scrapers in the pipeline."""
    
    @pytest.mark.asyncio
    async def test_scraper_execute_with_empty_context(self):
        """Scraper.execute() must handle empty context."""
        scraper = DBAScraper(debug=False)
        context = PipelineContext(
            query="test",
            listings=[],
            config={},
            errors=[],
            metadata={}
        )
        
        result = await scraper.execute(context)
        assert result is not None
        assert isinstance(result, PipelineContext)
        assert result.query == "test"
    
    @pytest.mark.asyncio
    async def test_scraper_execute_adds_listings(self):
        """Scraper.execute() must add scraped listings to context."""
        scraper = DBAScraper(debug=False)
        context = PipelineContext(
            query="test",
            listings=[],
            config={"max_results": 5},
            errors=[],
            metadata={}
        )
        
        # Mock the scrape method to return test data
        with patch.object(scraper, 'scrape', new_callable=AsyncMock) as mock_scrape:
            mock_listing = Mock()
            mock_listing.id = "test-1"
            mock_scrape.return_value = [mock_listing]
            
            result = await scraper.execute(context)
            
            # Verify scrape was called
            mock_scrape.assert_called_once()
            # Verify listing was added to context
            assert len(result.listings) > 0
    
    @pytest.mark.asyncio
    async def test_scraper_execute_handles_errors(self):
        """Scraper.execute() must handle errors gracefully."""
        scraper = DBAScraper(debug=False)
        context = PipelineContext(
            query="test",
            listings=[],
            config={},
            errors=[],
            metadata={}
        )
        
        # Mock scrape to raise an error
        with patch.object(scraper, 'scrape', new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Test error")
            
            result = await scraper.execute(context)
            
            # Should have an error in context
            assert len(result.errors) > 0
            assert result.errors[0].module_name == "dba-scraper"
            assert result.errors[0].error_type == "SCRAPE_ERROR"
