# Implementation Plan: Code Modularity

**Branch**: `001-code-modularity` | **Date**: 2025-05-20 | **Spec**: [specs/001-code-modularity/spec.md](../spec.md)

**Input**: Feature specification from `/specs/001-code-modularity/spec.md`

## Summary

Enhance the existing second-hand research agent codebase with formal modular architecture. Currently, the codebase has separate directories for scrapers, filters, processors, and reviewers, but lacks formal base classes, automatic discovery, and dependency injection. This feature formalizes the module system so that: (1) new platform scrapers can be added without modifying existing code, (2) LLM backends can be swapped via configuration, and (3) all modules can be tested in isolation.

## Technical Context

**Language/Version**: Python 3.10+

**Primary Dependencies**: httpx, beautifulsoup4, rich, python-dotenv, requests

**Storage**: N/A (scraping tool, no persistent storage)

**Testing**: pytest

**Target Platform**: CLI (Linux/macOS/Windows)

**Project Type**: cli

**Performance Goals**: Scraper modules complete requests in under 5 seconds, filter modules process batches in under 2 seconds, LLM-powered modules complete in under 10 seconds per batch, module initialization under 1 second

**Constraints**: Module failures must be isolated and not cause data loss; partial results from successful modules must be preserved

**Scale/Scope**: Unbounded scalability - support as many modules as practical without artificial limits

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|-----------|--------|---------------|
| I. CLI-First | ✅ PASS | All features accessible via CLI flags; text in/out protocol maintained |
| II. Modular Design | ✅ PASS | Feature explicitly implements modular design with independent, swappable modules |
| III. Test-First | ✅ PASS | Spec requires unit tests for all modules (SC-003: 90% coverage); FR-009 requires structured logging |

**Gate Status**: ✅ ALL PRINCIPLES SATISFIED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-code-modularity/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
second_hand_searcher/
├── second_hand_research.py    # Main CLI entry point
├── config.py                  # Configuration and constants
├── models.py                  # Data models (Listing, etc.)
├── output.py                  # Result formatting and display
├── utils.py                   # Utility functions
├── core/                      # NEW: Core modular infrastructure
│   ├── __init__.py
│   ├── registry.py            # Module registry for auto-discovery
│   └── injection.py           # Dependency injection container
├── scrapers/
│   ├── __init__.py
│   ├── base.py                # Base scraper class (formalized)
│   ├── dba.py                 # DBA.dk scraper
│   ├── vinted.py              # Vinted scraper
│   └── tradera.py             # Tradera scraper
├── filters/
│   ├── __init__.py
│   ├── base.py                # Base filter class (formalized)
│   ├── keyword_filter.py      # Keyword-based filtering
│   └── llm_filter.py          # LLM-based filtering
├── processors/
│   ├── __init__.py
│   ├── base.py                # Base processor class (formalized)
│   ├── description_fetcher.py
│   ├── price_converter.py
│   └── model_extractor.py
├── reviewers/
│   ├── __init__.py
│   ├── base.py                # Base reviewer class (new)
│   ├── search.py
│   └── summarizer.py
├── ranker.py                  # Ranking logic (to be modularized)
├── llm/                       # LLM integrations
│   ├── __init__.py
│   ├── base.py                # Base LLM client (new)
│   ├── gemini.py              # Google Gemini client
│   └── mistral.py             # Mistral AI client
└── tests/
    ├── test_scrapers.py
    ├── test_filters.py
    ├── test_processors.py
    └── test_llm.py
```

**Structure Decision**: Single project structure maintained. Existing directories (scrapers/, filters/, processors/, reviewers/) are preserved and enhanced with base classes. New `core/` directory added for modular infrastructure (registry, injection). LLM clients moved to `llm/` directory for better separation of concerns.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - all constitution principles are satisfied by design.
