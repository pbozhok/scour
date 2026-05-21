# Contract: Module Interface

**Feature**: Code Modularity (001-code-modularity)
**Type**: Internal API Contract
**Version**: 1.0
**Date**: 2025-05-20

## Overview

This contract defines the interface that all modules in the second-hand research agent must implement. It enables the pipeline orchestrator to work with any module type uniformly.

## Interface Definition

### Module (Abstract Base Class)

All modules MUST inherit from this base class and implement all abstract methods.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class PipelineContext:
    """
    The context object passed between modules in the pipeline.
    
    Attributes:
        query: The user's search query string
        listings: List of Listing objects being processed
        config: Configuration dictionary for this pipeline run
        errors: List of PipelineError objects accumulated
        metadata: Dictionary for timing, versions, and other metadata
    """
    query: str
    listings: List[Any]  # List[Listing] - actual type from models.py
    config: Dict[str, Any]
    errors: List[Dict[str, Any]]  # List[PipelineError] as dicts
    metadata: Dict[str, Any]

class Module(ABC):
    """
    Base class for all pipeline modules.
    
    Class Attributes:
        name: str - Unique identifier (e.g., "dba-scraper", "gemini-llm")
        module_type: str - One of: SCRAPER, FILTER, PROCESSOR, RANKER, REVIEWER, LLM
        version: str - Semantic version (e.g., "1.0.0")
        description: str - Human-readable description (optional)
    """
    
    name: str
    module_type: str
    version: str
    description: str = ""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the module with configuration.
        
        Args:
            config: Module-specific configuration dictionary
            
        Returns:
            bool: True if initialization succeeded, False otherwise
            
        Raises:
            ModuleInitializationError: If initialization fails fatally
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
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the module's primary function.
        
        This method must:
        1. Process the input context
        2. Perform its primary function (scrape, filter, process, etc.)
        3. Return a modified context
        4. Handle errors by adding PipelineError to context.errors, not raising
           (except for fatal errors that prevent any processing)
        
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
```

## Module Types

All modules must have a `module_type` that is one of the following:

| Type | Description | Example Modules |
|------|-------------|-----------------|
| `SCRAPER` | Extracts listings from marketplace platforms | dba, vinted, tradera, facebook-marketplace |
| `FILTER` | Filters listings based on criteria | keyword-filter, llm-filter |
| `PROCESSOR` | Transforms/augments listing data | price-converter, model-extractor, description-fetcher |
| `RANKER` | Scores and ranks listings | relevance-rank, quality-rank |
| `REVIEWER` | Fetches and summarizes product reviews | review-search, review-summarizer |
| `LLM` | Large Language Model client | gemini, mistral, anthropic |

## PipelineContext Methods

The PipelineContext class provides these helper methods:

```python
class PipelineContext:
    # ... attributes ...
    
    def add_listing(self, listing: Any) -> None:
        """Add a listing to the results."""
        self.listings.append(listing)
    
    def add_listings(self, listings: List[Any]) -> None:
        """Add multiple listings to the results."""
        self.listings.extend(listings)
    
    def add_error(self, module_name: str, error_type: str, message: str, 
                  severity: str = "ERROR", context: Dict = None) -> None:
        """Record an error that occurred during processing."""
        self.errors.append({
            "module_name": module_name,
            "error_type": error_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "context": context or {}
        })
    
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
```

## Error Handling

### Error Classification

Modules MUST classify errors using these severity levels:

- **ERROR**: Module failed to execute; partial results may be available
  - Example: Network connection failed, API key invalid, required config missing
  - Action: Add to `context.errors`, continue pipeline with partial results
  
- **WARNING**: Module executed but with non-fatal issues
  - Example: Some listings failed to parse, rate limit approached
  - Action: Add to `context.errors` with severity=WARNING, continue normally

### Error Dictionary Structure

Errors added to `context.errors` MUST have this structure:

```python
{
    "module_name": "scrapers.dba",
    "error_type": "NETWORK_ERROR",  # or "CONFIG_ERROR", "API_ERROR", etc.
    "message": "Connection timeout to dba.dk",
    "timestamp": "2025-05-20T10:00:00.123456",
    "severity": "ERROR",  # or "WARNING"
    "context": {
        "url": "https://dba.dk/search?q=...",
        "retry_count": 3,
        "last_error": "Timeout after 30s"
    }
}
```

## Module Lifecycle

```
                    ┌─────────────────────┐
                    │     UNINITIALIZED     │
                    └──────────┬──────────┘
                               │
               ┌───────────────┴───────────────┐
               │                           │
               ▼                           ▼
        ┌───────────────┐           ┌───────────────┐
        │     READY     │           │    INVALID    │
        └───────────────┘           └───────────────┘
               │
               │ initialize() or validate() fails
               ▼
        ┌───────────────┐
        │   EXECUTING   │◄──────────────────────────────┐
        └───────────────┘                             │
               │                                      │
               ▼                                      │
        ┌───────────────┐                             │
        │     READY     │◄────────────────────────────┘
        └───────────────┘         (execute() returns)
               │
               │ cleanup()
               ▼
        ┌───────────────┐
        │   CLEANED     │
        └───────────────┘
```

## Contract Testing

Modules MUST pass these contract tests:

```python
# Test 1: Interface compliance
def test_module_interface(module_class):
    assert hasattr(module_class, 'name')
    assert hasattr(module_class, 'module_type')
    assert hasattr(module_class, 'version')
    assert callable(getattr(module_class, 'initialize'))
    assert callable(getattr(module_class, 'validate'))
    assert callable(getattr(module_class, 'execute'))
    assert callable(getattr(module_class, 'cleanup'))

# Test 2: Module type validation
def test_module_type(module):
    valid_types = {'SCRAPER', 'FILTER', 'PROCESSOR', 'RANKER', 'REVIEWER', 'LLM'}
    assert module.module_type in valid_types

# Test 3: Context preservation
def test_context_preservation(module, context):
    original_query = context.query
    original_listings = len(context.listings)
    
    result = module.execute(context)
    
    assert result.query == original_query
    assert isinstance(result.listings, list)
    assert isinstance(result.errors, list)

# Test 4: Error accumulation
def test_error_accumulation(module, context):
    original_error_count = len(context.errors)
    result = module.execute(context)
    assert len(result.errors) >= original_error_count
```

## Versioning

Modules MUST follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to the interface
- **MINOR**: Backward-compatible new features
- **PATCH**: Backward-compatible bug fixes

When a module's MAJOR version changes, the pipeline orchestrator MUST handle it appropriately (warn user, disable module, etc.).

## Backward Compatibility

- Modules MUST maintain backward compatibility within the same MAJOR version
- Changes to PipelineContext MUST be additive (new optional fields) or have defaults
- Removing required fields from PipelineContext requires a MAJOR version bump
