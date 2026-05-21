# Quickstart: Code Modularity

**Feature**: Code Modularity (001-code-modularity)
**Date**: 2025-05-20

## Overview

This guide helps developers quickly understand and start using the modular architecture in the second-hand research agent.

## For Module Developers

### Creating a New Scraper Module

1. **Create the file** in `scrapers/` directory:
   ```bash
   touch scrapers/facebook_marketplace.py
   ```

2. **Implement the base interface**:
   ```python
   from scrapers.base import BaseScraper
   from models import Listing
   
   class FacebookMarketplaceScraper(BaseScraper):
       name = "facebook-marketplace"
       module_type = "SCRAPER"
       version = "1.0"
       
       def __init__(self):
           super().__init__()
           self.session = None
       
       def initialize(self, config: dict) -> bool:
           # Set up HTTP session, API keys, etc.
           self.session = create_session()
           return True
       
       def validate(self) -> bool:
           return self.session is not None
       
       def execute(self, context: PipelineContext) -> PipelineContext:
           # Scrape Facebook Marketplace for context.query
           listings = self._scrape(context.query)
           for listing in listings:
               context.add_listing(listing)
           return context
       
       def _scrape(self, query: str) -> List[Listing]:
           # Implementation here
           pass
   ```

3. **Add tests** in `tests/test_scrapers.py`:
   ```python
   def test_facebook_scraper_interface():
       scraper = FacebookMarketplaceScraper()
       assert scraper.name == "facebook-marketplace"
       assert scraper.module_type == "SCRAPER"
       # Test with mock responses
   ```

4. **Run tests**:
   ```bash
   pytest tests/test_scrapers.py -v
   ```

### Creating a New LLM Client

1. **Create the file** in `llm/` directory:
   ```bash
   touch llm/anthropic.py
   ```

2. **Implement the LLM interface**:
   ```python
   from llm.base import BaseLLMClient
   
   class AnthropicClient(BaseLLMClient):
       name = "anthropic"
       version = "1.0"
       
       def __init__(self, api_key: str):
           self.api_key = api_key
       
       def chat(self, messages: list, model: str = "claude-3-sonnet") -> str:
           # Call Anthropic API
           pass
   ```

3. **Register in config** (`config.py`):
   ```python
   LLM_PROVIDERS = {
       "gemini": {"class": "llm.gemini.GeminiClient", "api_key_env": "GOOGLE_API_KEY"},
       "mistral": {"class": "llm.mistral.MistralClient", "api_key_env": "MISTRAL_API_KEY"},
       "anthropic": {"class": "llm.anthropic.AnthropicClient", "api_key_env": "ANTHROPIC_API_KEY"},
   }
   ```

4. **Use via CLI**:
   ```bash
   python second_hand_research.py "iPhone 15" --llm anthropic
   ```

## For Users

### Swapping LLM Providers

Change the LLM provider by setting the `--llm` flag:

```bash
# Use Gemini (default)
python second_hand_research.py "query" --llm gemini

# Use Mistral
python second_hand_research.py "query" --llm mistral
```

Or via environment variable:
```bash
# Set default LLM
export DEFAULT_LLM=mistral
python second_hand_research.py "query"
```

### Disabling Specific Modules

Skip individual module types via CLI flags:

```bash
# Skip LLM-based filtering (faster, no API calls)
python second_hand_research.py "query" --no-filter

# Skip scoring (sort by price instead)
python second_hand_research.py "query" --no-score

# Skip review fetching
python second_hand_research.py "query" --no-reviews

# All three for fastest search
python second_hand_research.py "query" --no-filter --no-score --no-reviews
```

## Project Structure at a Glance

```
second_hand_searcher/
├── second_hand_research.py    # Main entry point (orchestrates pipeline)
├── config.py                  # Configuration (LLM providers, timeouts, etc.)
├── core/
│   ├── registry.py            # Module auto-discovery and registration
│   └── injection.py           # Dependency injection container
├── scrapers/                  # Platform scrapers
│   ├── base.py                # BaseScraper class
│   ├── dba.py                 # DBA.dk implementation
│   ├── vinted.py              # Vinted implementation
│   └── tradera.py             # Tradera implementation
├── filters/                   # Result filters
│   ├── base.py                # BaseFilter class
│   ├── keyword_filter.py      # Keyword matching
│   └── llm_filter.py          # LLM-based relevance
├── processors/                # Data processors
│   ├── base.py                # BaseProcessor class
│   ├── description_fetcher.py
│   ├── price_converter.py
│   └── model_extractor.py
├── reviewers/                 # Review handling
│   ├── base.py                # BaseReviewer class
│   ├── search.py
│   └── summarizer.py
├── llm/                       # LLM clients
│   ├── base.py                # BaseLLMClient class
│   ├── gemini.py
│   └── mistral.py
└── tests/                     # Unit tests
    ├── test_scrapers.py
    ├── test_filters.py
    ├── test_processors.py
    └── test_llm.py
```

## Testing Your Changes

```bash
# Run all tests
pytest

# Run tests for a specific module type
pytest tests/test_scrapers.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=scrapers --cov=filters --cov=processors
```

## Logging

All modules use structured logging:

```python
import logging
from core.logging import get_logger

logger = get_logger(__name__)

class MyModule(BaseModule):
    def execute(self, context):
        logger.info("Starting execution", query=context.query, listing_count=len(context.listings))
        try:
            # ... do work ...
            logger.debug("Processed listing", listing_id=listing.id)
        except Exception as e:
            logger.error("Execution failed", error=str(e), listing_id=listing.id)
            raise
```

Logs are output in JSON format for easy parsing:
```json
{"timestamp": "2025-05-20T10:00:00Z", "level": "INFO", "module": "scrapers.dba", "message": "Starting execution", "query": "iPhone 15", "listing_count": 0}
```

## Performance Targets

When developing modules, aim for:
- **Scrapers**: Complete within 5 seconds
- **Filters**: Process batches within 2 seconds  
- **LLM modules**: Complete within 10 seconds per batch
- **Module initialization**: Under 1 second

Test your module performance:
```python
import time

start = time.time()
result = module.execute(context)
elapsed = time.time() - start
assert elapsed < 5.0, f"Module {module.name} exceeded 5s target: {elapsed}s"
```
