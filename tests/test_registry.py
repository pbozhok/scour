"""
Tests for module registry functionality.
"""

import pytest
from unittest.mock import Mock

from core.module import Module, ModuleType, PipelineContext
from core.registry import ModuleRegistry


# ============================================================================
# Module Discovery Tests (T023 [P] [US1])
# ============================================================================

class TestModuleRegistry:
    """Tests for ModuleRegistry class."""
    
    def test_registry_starts_empty(self):
        """New registry must start with no modules."""
        registry = ModuleRegistry()
        assert len(registry.get_modules()) == 0
    
    def test_register_and_get_module(self):
        """Registry must be able to register and retrieve a module."""
        registry = ModuleRegistry()
        
        # Create a mock module
        mock_module = Mock(spec=Module)
        mock_module.name = "test-module"
        mock_module.module_type = ModuleType.SCRAPER
        
        registry.register(mock_module)
        retrieved = registry.get_module("test-module")
        
        assert retrieved is mock_module
    
    def test_get_nonexistent_module_returns_none(self):
        """Getting a non-existent module must return None."""
        registry = ModuleRegistry()
        assert registry.get_module("nonexistent") is None
    
    def test_get_modules_by_type(self):
        """Registry must filter modules by type."""
        registry = ModuleRegistry()
        
        # Create mock modules of different types
        scraper = Mock(spec=Module)
        scraper.name = "scraper-1"
        scraper.module_type = ModuleType.SCRAPER
        
        filter_mod = Mock(spec=Module)
        filter_mod.name = "filter-1"
        filter_mod.module_type = ModuleType.FILTER
        
        processor = Mock(spec=Module)
        processor.name = "processor-1"
        processor.module_type = ModuleType.PROCESSOR
        
        registry.register(scraper)
        registry.register(filter_mod)
        registry.register(processor)
        
        # Get only scrapers
        scrapers = registry.get_modules(ModuleType.SCRAPER)
        assert len(scrapers) == 1
        assert scrapers[0].name == "scraper-1"
        
        # Get only filters
        filters = registry.get_modules(ModuleType.FILTER)
        assert len(filters) == 1
        assert filters[0].name == "filter-1"
        
        # Get all modules
        all_modules = registry.get_modules()
        assert len(all_modules) == 3
    
    def test_unregister_module(self):
        """Registry must support unregistering modules."""
        registry = ModuleRegistry()
        
        mock_module = Mock(spec=Module)
        mock_module.name = "test-module"
        mock_module.module_type = ModuleType.SCRAPER
        
        registry.register(mock_module)
        assert registry.get_module("test-module") is mock_module
        
        result = registry.unregister("test-module")
        assert result is True
        assert registry.get_module("test-module") is None
    
    def test_unregister_nonexistent_returns_false(self):
        """Unregistering a non-existent module must return False."""
        registry = ModuleRegistry()
        result = registry.unregister("nonexistent")
        assert result is False
    
    def test_duplicate_registration_raises_error(self):
        """Registering a duplicate module name must raise ValueError."""
        registry = ModuleRegistry()
        
        mock_module1 = Mock(spec=Module)
        mock_module1.name = "duplicate"
        mock_module1.module_type = ModuleType.SCRAPER
        
        mock_module2 = Mock(spec=Module)
        mock_module2.name = "duplicate"
        mock_module2.module_type = ModuleType.SCRAPER
        
        registry.register(mock_module1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(mock_module2)
    
    def test_validate_all(self):
        """Registry must validate all registered modules."""
        registry = ModuleRegistry()
        
        # Create valid module
        valid_module = Mock(spec=Module)
        valid_module.name = "valid"
        valid_module.module_type = ModuleType.SCRAPER
        valid_module.validate = Mock(return_value=True)
        
        # Create invalid module
        invalid_module = Mock(spec=Module)
        invalid_module.name = "invalid"
        invalid_module.module_type = ModuleType.FILTER
        invalid_module.validate = Mock(return_value=False)
        
        registry.register(valid_module)
        registry.register(invalid_module)
        
        errors = registry.validate_all()
        assert len(errors) == 1
        assert "invalid" in errors[0]
    
    def test_validate_all_empty_registry(self):
        """Validating an empty registry must return empty list."""
        registry = ModuleRegistry()
        errors = registry.validate_all()
        assert errors == []


# ============================================================================
# Module Discovery from Directory Tests (T023 [P] [US1])
# ============================================================================

class TestModuleDiscoveryFromDirectory:
    """Tests for automatic module discovery from directories."""
    
    def test_discovery_paths_are_configured(self):
        """Registry must have discovery paths for all module types."""
        registry = ModuleRegistry()
        # Check that discovery paths are set up
        assert ModuleType.SCRAPER in registry._discovery_paths
        assert ModuleType.FILTER in registry._discovery_paths
        assert ModuleType.PROCESSOR in registry._discovery_paths
        assert ModuleType.REVIEWER in registry._discovery_paths
        assert ModuleType.LLM in registry._discovery_paths
        assert ModuleType.RANKER in registry._discovery_paths
    
    def test_discovery_path_values(self):
        """Discovery paths must point to correct directories."""
        registry = ModuleRegistry()
        assert registry._discovery_paths[ModuleType.SCRAPER] == "scrapers"
        assert registry._discovery_paths[ModuleType.FILTER] == "filters"
        assert registry._discovery_paths[ModuleType.PROCESSOR] == "processors"
        assert registry._discovery_paths[ModuleType.REVIEWER] == "reviewers"
        assert registry._discovery_paths[ModuleType.LLM] == "llm"


# ============================================================================
# Integration Tests: Scraper Discovery (T028 [US1])
# ============================================================================

class TestScraperDiscovery:
    """Integration tests for scraper module discovery."""
    
    def test_discover_existing_scrapers(self):
        """Registry must be able to discover scrapers from scrapers/ directory."""
        from core.registry import ModuleRegistry
        from scrapers.dba import DBAScraper
        from scrapers.vinted import VintedScraper
        from scrapers.tradera import TraderaScraper
        
        # Create a new registry and manually register our scrapers
        # (Auto-discovery is tested separately; this verifies the registry works)
        registry = ModuleRegistry()
        
        # Register known scrapers
        registry.register(DBAScraper(debug=False))
        registry.register(VintedScraper(debug=False))
        registry.register(TraderaScraper(debug=False))
        
        # Check that scrapers are registered
        scrapers = registry.get_modules(ModuleType.SCRAPER)
        scraper_names = {s.name for s in scrapers}
        
        assert "dba-scraper" in scraper_names
        assert "vinted-scraper" in scraper_names
        assert "tradera-scraper" in scraper_names
        assert len(scrapers) == 3
    
    def test_scrapers_have_unique_names(self):
        """All discovered scrapers must have unique names."""
        from scrapers.dba import DBAScraper
        from scrapers.vinted import VintedScraper
        from scrapers.tradera import TraderaScraper
        
        names = {DBAScraper.name, VintedScraper.name, TraderaScraper.name}
        assert len(names) == 3  # All names must be unique
    
    def test_scrapers_are_properly_typed(self):
        """All scrapers must be of type SCRAPER."""
        from scrapers.dba import DBAScraper
        from scrapers.vinted import VintedScraper
        from scrapers.tradera import TraderaScraper
        
        assert DBAScraper.module_type == ModuleType.SCRAPER
        assert VintedScraper.module_type == ModuleType.SCRAPER
        assert TraderaScraper.module_type == ModuleType.SCRAPER
