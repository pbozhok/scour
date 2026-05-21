"""
Pytest fixtures and utilities for testing the second-hand research agent.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, Mock, patch

from core.module import Module, ModuleType, PipelineContext, PipelineError
from models import Listing


# ============================================================================
# Fixtures: Pipeline Context
# ============================================================================

@pytest.fixture
def empty_context() -> PipelineContext:
    """Create an empty PipelineContext."""
    return PipelineContext(
        query="test query",
        listings=[],
        config={},
        errors=[],
        metadata={}
    )


@pytest.fixture
def sample_context() -> PipelineContext:
    """Create a PipelineContext with sample data."""
    sample_listing = Listing(
        id="123",
        title="Sample Product",
        price=100.0,
        currency="EUR",
        url="https://example.com/123",
        platform="test",
        description="Test description",
    )
    return PipelineContext(
        query="iPhone 15",
        listings=[sample_listing],
        config={"max_results": 10, "llm": "gemini"},
        errors=[],
        metadata={"timestamp": "2025-05-20T00:00:00Z"}
    )


@pytest.fixture
def context_with_errors() -> PipelineContext:
    """Create a PipelineContext with errors."""
    error = PipelineError(
        module_name="test-module",
        error_type="TEST_ERROR",
        message="Test error message",
        severity="WARNING",
        context={"key": "value"}
    )
    return PipelineContext(
        query="test",
        listings=[],
        config={},
        errors=[error],
        metadata={}
    )


# ============================================================================
# Fixtures: Mock Modules
# ============================================================================

@pytest.fixture
def mock_module() -> Mock:
    """Create a mock Module instance."""
    mock = Mock(spec=Module)
    mock.name = "mock-module"
    mock.module_type = ModuleType.SCRAPER
    mock.version = "1.0.0"
    mock.initialize = Mock(return_value=True)
    mock.validate = Mock(return_value=True)
    mock.execute = AsyncMock(return_value=PipelineContext(
        query="test",
        listings=[],
        config={},
        errors=[],
        metadata={}
    ))
    mock.cleanup = Mock()
    return mock


@pytest.fixture
def mock_scraper() -> Mock:
    """Create a mock scraper module."""
    from scrapers.base import BaseScraper
    mock = Mock(spec=BaseScraper)
    mock.name = "mock-scraper"
    mock.module_type = ModuleType.SCRAPER
    mock.version = "1.0.0"
    mock.platform = "mock"
    mock.initialize = Mock(return_value=True)
    mock.validate = Mock(return_value=True)
    mock.scrape = AsyncMock(return_value=[])
    mock.execute = AsyncMock(return_value=PipelineContext(
        query="test",
        listings=[],
        config={},
        errors=[],
        metadata={}
    ))
    mock.cleanup = Mock()
    return mock


@pytest.fixture
def mock_filter() -> Mock:
    """Create a mock filter module."""
    from filters.base import BaseFilter
    mock = Mock(spec=BaseFilter)
    mock.name = "mock-filter"
    mock.module_type = ModuleType.FILTER
    mock.version = "1.0.0"
    mock.initialize = Mock(return_value=True)
    mock.validate = Mock(return_value=True)
    mock.filter = AsyncMock(return_value=[])
    mock.execute = AsyncMock(return_value=PipelineContext(
        query="test",
        listings=[],
        config={},
        errors=[],
        metadata={}
    ))
    mock.cleanup = Mock()
    return mock


@pytest.fixture
def mock_processor() -> Mock:
    """Create a mock processor module."""
    from processors.base import BaseProcessor
    mock = Mock(spec=BaseProcessor)
    mock.name = "mock-processor"
    mock.module_type = ModuleType.PROCESSOR
    mock.version = "1.0.0"
    mock.initialize = Mock(return_value=True)
    mock.validate = Mock(return_value=True)
    mock.process = AsyncMock(return_value=[])
    mock.execute = AsyncMock(return_value=PipelineContext(
        query="test",
        listings=[],
        config={},
        errors=[],
        metadata={}
    ))
    mock.cleanup = Mock()
    return mock


@pytest.fixture
def mock_sample_listing() -> Listing:
    """Create a sample Listing for testing."""
    return Listing(
        id="test-123",
        title="Test Product",
        price=99.99,
        currency="EUR",
        url="https://example.com/test-123",
        platform="test-platform",
        description="This is a test product description.",
        model="TestModel",
        score=85.0,
        is_relevant=True,
        metadata={"color": "black", "condition": "new"}
    )


@pytest.fixture
def mock_listings() -> List[Listing]:
    """Create a list of sample listings."""
    return [
        Listing(
            id="1",
            title="Product 1",
            price=100.0,
            currency="EUR",
            url="https://example.com/1",
            platform="test",
            description="Description 1",
        ),
        Listing(
            id="2",
            title="Product 2",
            price=200.0,
            currency="DKK",
            url="https://example.com/2",
            platform="test",
            description="Description 2",
        ),
        Listing(
            id="3",
            title="Product 3",
            price=300.0,
            currency="SEK",
            url="https://example.com/3",
            platform="test",
            description="Description 3",
        ),
    ]


# ============================================================================
# Fixtures: Module Factories
# ============================================================================

@pytest.fixture
def module_config() -> Dict[str, Any]:
    """Sample module configuration."""
    return {
        "api_key": "test-api-key",
        "timeout": 30,
        "retries": 3,
        "debug": True,
    }


@pytest.fixture
def mock_module_factory():
    """Factory for creating mock modules of different types."""
    def _create_module(
        module_type: ModuleType = ModuleType.SCRAPER,
        name: str = "test-module",
        validate_return: bool = True,
        execute_return: Optional[PipelineContext] = None,
    ) -> Mock:
        mock = Mock(spec=Module)
        mock.name = name
        mock.module_type = module_type
        mock.version = "1.0.0"
        mock.initialize = Mock(return_value=True)
        mock.validate = Mock(return_value=validate_return)
        mock.execute = AsyncMock(return_value=execute_return or PipelineContext(
            query="test",
            listings=[],
            config={},
            errors=[],
            metadata={}
        ))
        mock.cleanup = Mock()
        return mock
    
    return _create_module


# ============================================================================
# Fixtures: Registry
# ============================================================================

@pytest.fixture
def empty_registry():
    """Create an empty ModuleRegistry."""
    from core.registry import ModuleRegistry
    return ModuleRegistry()


@pytest.fixture
def populated_registry(mock_scraper, mock_filter):
    """Create a ModuleRegistry with some modules."""
    from core.registry import ModuleRegistry
    reg = ModuleRegistry()
    reg.register(mock_scraper)
    reg.register(mock_filter)
    return reg


# ============================================================================
# Fixtures: Dependency Injection
# ============================================================================

@pytest.fixture
def empty_container():
    """Create an empty Container."""
    from core.injection import Container
    return Container()


# ============================================================================
# Fixtures: Patching
# ============================================================================

@pytest.fixture
def patch_get_client():
    """Patch llm.get_client to return a mock."""
    with patch('llm.get_client') as mock_get_client:
        mock_client = Mock()
        mock_client.chat = AsyncMock(return_value="test response")
        mock_client.request_json = AsyncMock(return_value={"key": "value"})
        mock_get_client.return_value = mock_client
        yield mock_get_client


@pytest.fixture
def patch_httpx():
    """Patch httpx.AsyncClient for testing scrapers."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.text = '<html><body>Test HTML</body></html>'
        mock_response.status_code = 200
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        yield mock_client_class
