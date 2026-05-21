# Data Model: Code Modularity

**Feature**: Code Modularity (001-code-modularity)
**Date**: 2025-05-20
**Spec**: [specs/001-code-modularity/spec.md](./spec.md)

## Entities

### Module

A self-contained component with a single responsibility in the research pipeline.

**Attributes**:
- `name: str` - Unique identifier for the module (e.g., "dba-scraper", "gemini-llm")
- `type: ModuleType` - Category of module (SCRAPER, FILTER, PROCESSOR, RANKER, REVIEWER, LLM)
- `version: str` - Version identifier (e.g., "1.0")
- `description: str` - Human-readable description of what the module does
- `author: str` - Module author/maintainer
- `dependencies: List[str]` - Names of other modules this module requires

**Methods (Interface)**:
- `initialize(config: dict) -> bool` - Set up the module with configuration
- `validate() -> bool` - Verify module is properly configured
- `execute(context: PipelineContext) -> PipelineContext` - Perform the module's primary function
- `cleanup() -> None` - Release any resources (optional)

**Validation Rules**:
- `name` must be unique within its type
- `type` must be one of the defined ModuleType enum values
- `version` must follow semantic versioning format
- `initialize()` must be called before `execute()`

**State Transitions**:
```
UNINITIALIZED --initialize--> READY --execute--> RUNNING --execute--> READY
                       \--validate--> VALID/INVALID
                              \--cleanup--> CLEANED
```

---

### ModuleType (Enum)

Categories of modules in the system.

**Values**:
- `SCRAPER` - Extracts listings from marketplace platforms
- `FILTER` - Filters listings based on criteria (keyword or LLM)
- `PROCESSOR` - Transforms/augments listing data (price conversion, model extraction)
- `RANKER` - Scores and ranks listings by relevance/quality
- `REVIEWER` - Fetches and summarizes product reviews
- `LLM` - Large Language Model client for AI-powered operations

---

### PipelineContext

The data container passed between modules in the research pipeline.

**Attributes**:
- `query: str` - The user's search query
- `listings: List[Listing]` - Current set of listings being processed
- `config: dict` - Configuration options for this pipeline run
- `errors: List[PipelineError]` - Accumulated errors from modules
- `metadata: dict` - Additional context (timing, module versions, etc.)

**Methods**:
- `add_listing(listing: Listing) -> None` - Add a listing to the results
- `add_error(error: PipelineError) -> None` - Record an error
- `get_listings() -> List[Listing]` - Get current listings
- `get_config(key: str, default=None) -> Any` - Get config value

**Validation Rules**:
- `query` must be non-empty string
- `listings` is a list (can be empty)
- `errors` is a list (can be empty)

---

### Listing

Represents a product listing from a marketplace.

**Attributes**:
- `id: str` - Unique identifier (platform-specific)
- `title: str` - Listing title
- `price: float` - Price in original currency
- `currency: str` - Original currency code (EUR, DKK, SEK)
- `url: str` - Direct URL to the listing
- `platform: str` - Source platform name (dba, vinted, tradera)
- `description: str` - Full description (may be truncated)
- `model: str` - Extracted product model (optional)
- `score: float` - Relevance score (0-100, optional)
- `is_relevant: bool` - Whether listing matches query (optional)
- `metadata: dict` - Platform-specific metadata

**Validation Rules**:
- `id` must be unique within a pipeline run
- `title` must be non-empty
- `price` must be positive number
- `currency` must be in supported currencies
- `url` must be valid HTTP/HTTPS URL
- `platform` must be non-empty

---

### PipelineError

Represents an error that occurred during pipeline execution.

**Attributes**:
- `module_name: str` - Name of the module that produced the error
- `error_type: str` - Type/category of error
- `message: str` - Human-readable error message
- `timestamp: datetime` - When the error occurred
- `severity: ErrorSeverity` - ERROR or WARNING
- `context: dict` - Additional error context

---

### ErrorSeverity (Enum)

**Values**:
- `ERROR` - Module failed to execute, partial results may be available
- `WARNING` - Module executed but with non-fatal issues

---

### ModuleConfig

Configuration for a specific module.

**Attributes**:
- `enabled: bool` - Whether the module is active
- `options: dict` - Module-specific configuration options
- `timeout: int` - Maximum execution time in seconds (default: 30)
- `retries: int` - Maximum retry attempts (default: 0)

---

## Relationships

```
PipelineContext --1--> Query
PipelineContext --*--> Listing
PipelineContext --*--> PipelineError

Module --1--> ModuleType
Module --*--> ModuleConfig (via dependencies)

Listing --1--> Platform
```

## Module Registry

The central registry that manages all available modules.

**Attributes**:
- `modules: Dict[ModuleType, List[Module]]` - Registered modules by type
- `configs: Dict[str, ModuleConfig]` - Configuration for each module

**Methods**:
- `register(module: Module) -> None` - Add a module to the registry
- `unregister(module_name: str) -> bool` - Remove a module
- `get_modules(module_type: ModuleType) -> List[Module]` - Get all modules of a type
- `get_module(module_name: str) -> Module` - Get a specific module
- `load_all() -> None` - Discover and load all modules from designated directories
- `validate_all() -> List[str]` - Validate all registered modules, return list of errors

## Contract: Module Interface

All modules must implement the following interface:

```python
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class PipelineContext:
    query: str
    listings: list
    config: dict
    errors: list
    metadata: dict

class Module(ABC):
    """Base class for all modules."""
    
    name: str
    module_type: str
    version: str
    
    @abstractmethod
    def initialize(self, config: dict) -> bool:
        """Initialize the module with configuration."""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate the module is properly configured."""
        pass
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute the module's primary function."""
        pass
    
    def cleanup(self) -> None:
        """Clean up resources. Optional override."""
        pass
```
