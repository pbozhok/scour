"""
Base Module classes for the second-hand research agent.

Defines the abstract base classes that all pipeline modules must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional


class ModuleType(Enum):
    """Categories of modules in the pipeline."""
    PREPROCESSOR = "PREPROCESSOR"
    SCRAPER = "SCRAPER"
    PROCESSOR = "PROCESSOR"
    FILTER = "FILTER"
    REVIEWER = "REVIEWER"
    RANKER = "RANKER"
    LLM = "LLM"


@dataclass
class PipelineError:
    """Represents an error that occurred during pipeline execution."""
    module_name: str
    error_type: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    severity: str = "ERROR"
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """
    The context object passed between modules in the research pipeline.
    
    This class carries all the data needed for modules to perform their
    functions, including the query, current listings, configuration, errors,
    and metadata.
    """
    query: str
    listings: List[Any] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    errors: List[PipelineError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_listing(self, listing: Any) -> None:
        """Add a listing to the results."""
        self.listings.append(listing)
    
    def add_listings(self, listings: List[Any]) -> None:
        """Add multiple listings to the results."""
        self.listings.extend(listings)
    
    def add_error(self, module_name: str, error_type: str, message: str, 
                  severity: str = "ERROR", context: Optional[Dict] = None) -> None:
        """Record an error that occurred during processing."""
        self.errors.append(PipelineError(
            module_name=module_name,
            error_type=error_type,
            message=message,
            severity=severity,
            context=context or {}
        ))
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def get_listings(self) -> List[Any]:
        """Get current listings (alias for listings attribute)."""
        return self.listings
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value."""
        return self.metadata.get(key, default)


class Module(ABC):
    """
    Base class for all pipeline modules.
    
    All modules must inherit from this class and implement the abstract methods.
    A module represents a self-contained component with a single responsibility
    in the research pipeline.
    
    Class Attributes:
        name: str - Unique identifier (e.g., "dba-scraper", "gemini-llm")
        module_type: ModuleType - Category of module
        version: str - Semantic version (e.g., "1.0.0")
        description: str - Human-readable description (optional)
    """
    
    name: str = ""
    module_type: ModuleType = ModuleType.PROCESSOR  # Default, should be overridden
    version: str = "1.0.0"
    description: str = ""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the module with configuration.
        
        Args:
            config: Module-specific configuration dictionary
            
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate that the module is properly configured and ready to execute.
        
        Returns:
            bool: True if module is valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the module's primary function.
        
        This method must:
        1. Process the input context
        2. Perform its primary function (scrape, filter, process, etc.)
        3. Return a modified context
        4. Handle errors by adding PipelineError to context.errors
        
        Args:
            context: The pipeline context containing current state
            
        Returns:
            PipelineContext: Modified context with updated listings, errors, metadata
        """
        pass
    
    def cleanup(self) -> None:
        """
        Clean up any resources held by the module.
        
        Called when the module is no longer needed. Override to release
        network connections, file handles, API clients, etc.
        
        Note: This method should be idempotent (safe to call multiple times).
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, type={self.module_type.value!r})"
