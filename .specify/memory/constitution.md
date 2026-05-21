# Second-Hand Research Agent Constitution

## Core Principles

### I. CLI-First
Every feature must be accessible via command-line interface. Text in/out protocol: args → stdout, errors → stderr. Support human-readable output by default, JSON for programmatic use.

### II. Modular Design
Scrapers, filters, processors, and rankers are independent modules. Each module has a single responsibility, clear interface, and can be bypassed or swapped.

### III. Test-First
New features require tests before implementation. Critical paths (scraping, filtering, ranking) must have unit and integration tests. Bug fixes include regression tests.

## Development Workflow

All changes go through PR review. Constitution violations block merging. Amendments to this constitution require documented justification.

## Governance

Constitution supersedes all other practices. Amendments require documentation and approval.

**Version**: 1.0.0 | **Ratified**: 2025-05-20 | **Last Amended**: 2025-05-20
