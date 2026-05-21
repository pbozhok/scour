# Second-Hand Product Research Agent

A powerful research assistant that scrapes, filters, and ranks second-hand product listings from multiple platforms using AI.

## Features

- **Multi-Platform Scraping**: Search DBA, Vinted, and Tradera simultaneously
- **AI-Powered Filtering**: Uses LLM to identify relevant listings based on your query
- **Intelligent Scoring**: Ranks results by relevance using AI analysis
- **Review Summarization**: Extracts and summarizes product reviews
- **Currency Conversion**: Automatic conversion between EUR, DKK, and SEK
- **Model Extraction**: Identifies product models from listing titles and descriptions
- **Flexible Configuration**: Skip any AI step for faster, simpler searches

## Platforms Supported

| Platform | Region | Status |
|----------|--------|--------|
| DBA | Denmark | ✅ Active |
| Vinted | Europe | ✅ Active |
| Tradera | Sweden | ✅ Active |

## Requirements

- Python 3.10+
- Required packages: `httpx`, `beautifulsoup4`, `rich`, `python-dotenv`, `requests`

## Installation

```bash
# Clone the repository
git clone https://github.com/pbozhok/second_hand_searcher.git
cd second_hand_searcher

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install httpx beautifulsoup4 rich python-dotenv requests
```

## API Keys

Create a `.env` file in the project root with your API keys:

```bash
# For Google Gemini (default LLM)
GOOGLE_API_KEY=your_gemini_api_key_here
# or
GEMINI_API_KEY=your_gemini_api_key_here

# For Mistral AI (alternative LLM)
MISTRAL_API_KEY=your_mistral_api_key_here

# Optional: For better review extraction via SerpAPI
SERPAPI_KEY=your_serpapi_key_here
```

> **Note**: Without SERPAPI_KEY, the agent falls back to free DuckDuckGo scraping for reviews.

## Usage

### Basic Search

```bash
# Default: uses Gemini LLM
python second_hand_research.py "iPhone 13 Pro"

# With Mistral LLM
python second_hand_research.py "Sony WH-1000XM5" --llm mistral

# Enable debug logging
python second_hand_research.py "MacBook Pro M2" --debug
```

### Advanced Options

| Option | Description | Default |
|--------|-------------|---------|
| `--llm` | LLM backend: `gemini` or `mistral` | `gemini` |
| `--currency` | Target currency: `EUR`, `DKK`, `SEK` | `EUR` |
| `--no-reviews` | Skip review extraction and summarization | Enabled |
| `--no-filter` | Skip LLM-based filtering (uses keyword matching) | Enabled |
| `--no-score` | Skip LLM-based scoring (sorts by price) | Enabled |
| `--debug` | Enable verbose debug logging | Disabled |

### Examples

```bash
# Fast search without AI processing
python second_hand_research.py "Nikon Z6" --no-filter --no-score --no-reviews

# Full AI-powered research with Mistral
python second_hand_research.py "Dyson V15" --llm mistral --currency DKK --debug

# Search in Swedish Krona
python second_hand_research.py "Samsung Galaxy S23" --currency SEK
```

## Project Structure

```
second_hand_searcher/
├── second_hand_research.py    # Main entry point (legacy + new pipeline)
├── config.py                  # Configuration and constants
├── models.py                  # Data models (Listing, etc.)
├── output.py                  # Result formatting and display
├── ranker.py                  # LLM-based ranking logic
├── utils.py                   # Utility functions
├── agents/                    # Agent implementations
├── core/                      # Core modular architecture (NEW)
│   ├── __init__.py            # Core module exports
│   ├── module.py              # Base Module ABC + ModuleType enum
│   ├── registry.py            # Module auto-discovery and registration
│   ├── injection.py           # Dependency injection container
│   ├── logging.py             # Structured JSON logging
│   └── pipeline.py            # Modular pipeline orchestrator
├── scrapers/                  # Platform scrapers
│   ├── __init__.py            # Scraper exports + auto-registration
│   ├── base.py                # BaseScraper (extends Module)
│   ├── dba.py                 # DBA.dk scraper
│   ├── vinted.py              # Vinted scraper
│   └── tradera.py             # Tradera scraper
├── filters/                   # Filtering modules
│   ├── __init__.py            # Filter exports + auto-registration
│   ├── base.py                # BaseFilter (extends Module)
│   ├── keyword_filter.py      # Keyword-based filtering
│   └── llm_filter.py          # LLM-based filtering
├── processors/                # Data processors
│   ├── __init__.py            # Processor exports + auto-registration
│   ├── base.py                # BaseProcessor (extends Module)
│   ├── description_fetcher.py # Fetches full descriptions
│   ├── price_converter.py     # Currency conversion
│   ├── model_extractor.py     # Extracts product models (uses LLM)
│   └── query_preprocessor.py  # Query preprocessing
├── reviewers/                 # Review modules
│   ├── __init__.py            # Reviewer exports
│   ├── base.py                # BaseReviewer (extends Module)
│   ├── search.py              # Review search
│   └── summarizer.py          # Review summarization
├── llm/                       # LLM client implementations
│   ├── __init__.py            # LLM exports + factory
│   ├── base.py                # BaseLLMClient (extends Module)
│   └── client.py              # GeminiClient, MistralClient, get_client()
└── tests/                     # Test suite
    ├── conftest.py            # Pytest fixtures
    ├── test_scrapers.py        # Scraper contract tests
    ├── test_filters.py         # Filter contract tests
    ├── test_processors.py      # Processor contract tests
    ├── test_reviewers.py       # Reviewer contract tests
    ├── test_llm.py             # LLM contract tests
    ├── test_llm_config.py      # LLM config tests
    ├── test_pipeline.py        # Pipeline tests
    ├── test_registry.py         # Registry tests
    └── integration/            # Integration tests
```

## Modular Architecture (NEW)

The project has been refactored to use a **modular, pluggable architecture** that enables:

- **Easy extensibility**: Add new scrapers, filters, or processors without modifying core code
- **Dependency injection**: Modules receive their dependencies (like LLM clients) automatically
- **Auto-discovery**: New modules are automatically discovered and registered
- **Error isolation**: Failures in one module don't stop the entire pipeline
- **Testability**: Each module can be tested in isolation

### Module Types

| Type | Purpose | Examples |
|------|---------|----------|
| `SCRAPER` | Fetch listings from platforms | DBAScraper, VintedScraper, TraderaScraper |
| `FILTER` | Filter listings for relevance | KeywordFilter, LLMFilter |
| `PROCESSOR` | Transform/augment listing data | PriceConverter, ModelExtractor, DescriptionFetcher |
| `REVIEWER` | Fetch and summarize reviews | ReviewSearcher, ReviewSummarizer |
| `LLM` | LLM provider implementations | GeminiClient, MistralClient |

### Pipeline Flow

The new modular pipeline (`--new-pipeline` flag) processes queries through these stages:

```
Query → [SCRAPER] → [PROCESSOR] → [FILTER] → [RANKER] → [REVIEWER] → Results
```

Each stage runs all registered modules of that type. For example:
- **SCRAPER stage**: Runs DBA, Vinted, and Tradera scrapers concurrently
- **PROCESSOR stage**: Runs PriceConverter, ModelExtractor, DescriptionFetcher
- **FILTER stage**: Runs KeywordFilter and/or LLMFilter

### Using the New Pipeline

```bash
# Use the new modular pipeline
python second_hand_research.py "iPhone 15" --new-pipeline

# With all options
python second_hand_research.py "iPhone 15" --new-pipeline --llm gemini --currency EUR --debug
```

### Adding a New Scraper

To add support for a new platform (e.g., Facebook Marketplace):

1. Create a new file `scrapers/facebook.py`:

```python
from scrapers.base import BaseScraper
from core.module import ModuleType
from models import Listing
import config

class FacebookScraper(BaseScraper):
    name = "facebook-scraper"
    module_type = ModuleType.SCRAPER
    version = "1.0.0"
    platform = "Facebook"
    
    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
        # Your scraping implementation here
        listings = []
        # ... fetch listings from Facebook ...
        return listings
```

2. The scraper is **automatically registered** via `scrapers/__init__.py`
3. That's it! The pipeline will discover and use it automatically.

### Adding a New Filter

To add a custom filter (e.g., price range filter):

```python
from filters.base import BaseFilter
from core.module import ModuleType, PipelineContext
from typing import List, Any

class PriceRangeFilter(BaseFilter):
    name = "price-range-filter"
    module_type = ModuleType.FILTER
    version = "1.0.0"
    
    def __init__(self, min_price: float = 0, max_price: float = 10000):
        super().__init__()
        self.min_price = min_price
        self.max_price = max_price
    
    async def filter(self, listings: List[Any], query: str, context: dict) -> List[Any]:
        return [l for l in listings if self.min_price <= l.price <= self.max_price]
```

Then use it in your pipeline configuration.

### Swapping LLM Backends

The architecture supports easy LLM backend swapping:

```python
# In your code
from llm import get_client

# Use Gemini (default)
llm_client = get_client("gemini")

# Or use Mistral
llm_client = get_client("mistral")
```

Modules that use LLM (like `LLMFilter`, `ModelExtractor`) automatically get the configured backend via the `llm_backend` config setting.

## How It Works

1. **Scraping**: Simultaneously searches all configured platforms for listings matching your query
2. **Deduplication**: Removes duplicate listings (same product across platforms)
3. **Filtering**: Uses LLM to determine which listings are relevant to your query
4. **Model Extraction**: Identifies exact product models from titles/descriptions
5. **Scoring**: LLM evaluates and scores each listing's quality and relevance
6. **Review Summarization**: Fetches and summarizes user reviews for top results
7. **Ranking**: Sorts all results by score and presents them in a formatted table

## Configuration

### Main Configuration (`config.py`)

Edit `config.py` to customize:

```python
# Scraper settings
SCRAPER_TIMEOUT = 20          # Request timeout in seconds
MAX_RETRIES = 5               # Max retry attempts
BATCH_SIZE = 20               # LLM processing batch size
DEFAULT_MAX_RESULTS = 40      # Max results per platform

# Currency exchange rates
EXCHANGE_RATES = {
    "EUR": 1.0,
    "DKK": 7.45,
    "SEK": 11.20,
}

# Review settings
MAX_REVIEW_RESULTS = 3       # Max reviews to fetch
REVIEW_DELAY = 4.0           # Delay between review searches

# LLM Providers (NEW)
LLM_PROVIDERS = {
    "gemini": "llm.client.GeminiClient",
    "mistral": "llm.client.MistralClient",
}
```

### LLM Configuration

The project supports **multiple LLM backends** that can be swapped via configuration:

| Backend | API Key Variable | Python Library | Notes |
|---------|-----------------|----------------|-------|
| Google Gemini | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | None (uses CLI) | Requires [Gemini CLI](https://github.com/google/gemini-cli) |
| Mistral AI | `MISTRAL_API_KEY` | `mistralai` | `pip install mistralai` |

**CLI Usage:**

```bash
# Use Gemini (default)
python second_hand_research.py "query" --llm gemini

# Use Mistral
python second_hand_research.py "query" --llm mistral
```

**Programmatic Usage:**

```python
from llm import get_client

# Get client by name
client = get_client("gemini")  # Returns GeminiClient
client = get_client("mistral")  # Returns MistralClient

# Use in modules
# Modules automatically receive the configured LLM backend via their config
```

### Adding a New LLM Backend

To add support for a new LLM provider (e.g., OpenAI):

1. Add to `config.py`:
```python
LLM_PROVIDERS = {
    "gemini": "llm.client.GeminiClient",
    "mistral": "llm.client.MistralClient",
    "openai": "llm.client.OpenAIClient",
}
```

2. Create `llm/client.py` class:
```python
class OpenAIClient(LLMClient):
    name = "openai-client"
    version = "1.0.0"
    
    async def chat(self, prompt: str, temperature: float = 0.0, max_retries: int = 5) -> str:
        # Implement OpenAI API call
        pass
```

3. Use it:
```bash
python second_hand_research.py "query" --llm openai
```

## Output

Results are displayed in a rich terminal table with the following columns:

- **Relevant**: Whether the listing matches your query (AI-determined)
- **Title**: Listing title
- **Price**: Price in your selected currency
- **Platform**: Source platform (DBA/Vinted/Tradera)
- **Model**: Extracted product model
- **Score**: AI-generated quality score (0-100)
- **URL**: Direct link to the listing

## Testing

The project has a **comprehensive test suite** following the Test-First principle:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_scrapers.py

# Run with verbose output
pytest -v

# Run only contract tests
pytest tests/test_scrapers.py tests/test_filters.py tests/test_processors.py tests/test_reviewers.py tests/test_llm.py

# Run only integration tests
pytest tests/integration/

# Run with test coverage
pytest --cov=.
```

### Test Organization

| Test File | Purpose | Tests |
|-----------|---------|-------|
| `test_scrapers.py` | Scraper contract and unit tests | 22 |
| `test_filters.py` | Filter contract and unit tests | 20 |
| `test_processors.py` | Processor contract and unit tests | 22 |
| `test_reviewers.py` | Reviewer contract tests | 8 |
| `test_llm.py` | LLM client contract tests | 21 |
| `test_llm_config.py` | LLM configuration tests | 8 |
| `test_pipeline.py` | Pipeline orchestrator tests | 18 |
| `test_registry.py` | Module registry tests | 15 |
| `integration/` | Integration tests | 18 |

**Total: ~150+ tests**

### Module Interface Tests

Each module type has **contract tests** that verify the interface:

- `BaseScraper` → All scrapers must implement `scrape()`, `initialize()`, `validate()`, `execute()`
- `BaseFilter` → All filters must implement `filter()`, `initialize()`, `validate()`, `execute()`
- `BaseProcessor` → All processors must implement `process()`, `initialize()`, `validate()`, `execute()`
- `BaseReviewer` → All reviewers must implement `review()`, `initialize()`, `validate()`, `execute()`
- `BaseLLMClient` → All LLM clients must implement `chat()`, `initialize()`, `validate()`

### Adding Tests for New Modules

When adding a new module, create corresponding tests:

```python
# tests/test_my_module.py
import pytest
from my_module import MyModule
from core.module import ModuleType

class TestMyModuleContract:
    def test_inherits_from_module(self):
        assert issubclass(MyModule, Module)
    
    def test_has_required_attributes(self):
        module = MyModule()
        assert module.name == "my-module"
        assert module.module_type == ModuleType.PROCESSOR
        assert module.version == "1.0.0"
    
    def test_has_required_methods(self):
        assert hasattr(MyModule, 'initialize')
        assert hasattr(MyModule, 'validate')
        assert hasattr(MyModule, 'execute')
    
    @pytest.mark.asyncio
    async def test_execute_returns_context(self):
        module = MyModule()
        context = PipelineContext(query="test")
        result = await module.execute(context)
        assert isinstance(result, PipelineContext)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Yes (for Gemini) | Google Gemini API key |
| `MISTRAL_API_KEY` | Yes (for Mistral) | Mistral API key |
| `SERPAPI_KEY` | No | Optional SerpAPI key for better reviews |

## Tips

1. **Start simple**: Use `--no-filter --no-score --no-reviews` for quick tests
2. **Batch processing**: For many queries, consider adding delays between requests
3. **API limits**: Be aware of your LLM provider's rate limits
4. **Currency**: Prices are converted using approximate exchange rates

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with [Gemini](https://ai.google.dev/) and [Mistral AI](https://mistral.ai/)
- Uses [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Scraping powered by [httpx](https://www.python-httpx.org/) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
