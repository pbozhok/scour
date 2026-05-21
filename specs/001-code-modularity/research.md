# Research: Code Modularity

**Feature**: Code Modularity (001-code-modularity)
**Date**: 2025-05-20
**Spec**: [specs/001-code-modularity/spec.md](./spec.md)

## Overview

Research conducted to inform the implementation of a formal modular architecture for the second-hand research agent. All NEEDS CLARIFICATION from the spec have been resolved through the clarification session.

## Decisions

### Decision 1: Performance Targets

**Decision**: Define explicit performance budgets per module type: scrapers <5s, filters <2s, LLM calls <10s

**Rationale**: 
- Scrapers involve network I/O, 5s is reasonable for marketplace websites
- Filters process in-memory data, 2s is aggressive but achievable
- LLM calls are the slowest; 10s accounts for API latency and processing
- Aligns with user expectations for a CLI research tool

**Alternatives considered**:
- No explicit targets: Rejected because measurable criteria are needed for testing
- End-to-end only: Rejected because individual module performance affects composition
- More aggressive targets: Rejected as unrealistic for network-bound operations

---

### Decision 2: Runtime Failure Handling

**Decision**: Isolate the failing module and continue processing with remaining modules, logging the error

**Rationale**:
- Maximizes result completeness - one bad module doesn't break entire search
- Aligns with CLI-First principle - users expect partial results over total failure
- Logging enables debugging without disrupting user flow
- Matches existing behavior in current codebase (errors in one scraper don't stop others)

**Alternatives considered**:
- Fail entire operation: Rejected as too brittle for a multi-platform tool
- Silent skip: Rejected because users need to know about failures
- Retry logic: Can be added later as enhancement, but isolation is the core requirement

---

### Decision 3: Reliability Guarantees

**Decision**: Module failures must not cause data loss; partial results should be preserved

**Rationale**:
- Users invest time in searches; losing all results due to one module failure is unacceptable
- Partial results are still valuable for research purposes
- Enables progressive enhancement - users can see what worked while debugging what didn't

**Alternatives considered**:
- All-or-nothing: Rejected as too strict for a research tool
- No guarantee: Rejected as it would violate user trust

---

### Decision 4: Scalability Approach

**Decision**: No explicit scalability requirements - support as many modules as practical

**Rationale**:
- Current use case (3 platforms) is small; artificial limits would be premature
- Python's import system handles module discovery efficiently
- Performance targets per module ensure scalability through composition
- Can add limits later if performance testing reveals issues

**Alternatives considered**:
- Fixed limit (e.g., 10 modules): Rejected as arbitrary
- Linear performance requirement: Rejected as hard to measure and enforce

---

### Decision 5: Observability Requirements

**Decision**: Each module must implement structured logging for its operations and errors

**Rationale**:
- Structured logging enables log aggregation and analysis tools
- Per-module logging allows tracing issues to specific components
- Aligns with Test-First principle - logs aid in debugging test failures
- Minimal overhead for CLI tool

**Alternatives considered**:
- Centralized logging only: Rejected because it obscures which module generated logs
- No requirement: Rejected as it would hinder debugging
- External monitoring: Rejected as overkill for CLI tool

## Best Practices Applied

### Module Design Patterns

1. **Base Class Pattern**: All modules inherit from abstract base classes defining the interface
2. **Registry Pattern**: Central registry for module discovery and lifecycle management
3. **Dependency Injection**: Modules receive dependencies via constructor, not hardcoded
4. **Strategy Pattern**: Different LLM providers as interchangeable strategies

### Python-Specific Patterns

1. **ABC (Abstract Base Class)**: Use `abc.ABC` and `@abstractmethod` for module interfaces
2. **Entry Points**: Consider using `pkg_resources` or `importlib.metadata` for discovery
3. **Type Hints**: All module interfaces use Python type hints for better IDE support
4. **Context Managers**: Use for resource cleanup (HTTP sessions, API clients)

### Testing Patterns

1. **Mocking**: Use `unittest.mock` for external dependencies in unit tests
2. **Factory Pattern**: Test factories for creating module instances with test doubles
3. **Contract Testing**: Verify all modules implement the required interface

## Technology Choices

### Module Discovery
- **Approach**: File-based discovery in designated directories (`scrapers/`, `filters/`, etc.)
- **Implementation**: Scan for Python files, import modules, check for base class inheritance
- **Rationale**: Simple, explicit, matches existing project structure

### Dependency Injection Container
- **Approach**: Simple registry-based DI, not a full framework
- **Implementation**: Dictionary-based container with explicit binding
- **Rationale**: Lightweight, no external dependencies, sufficient for CLI tool

### Logging Framework
- **Approach**: Python's built-in `logging` module with structured formatters
- **Implementation**: JSON formatter for structured logs, standard streams
- **Rationale**: Already in use in project, no new dependencies

## References

- Python `abc` module documentation
- Dependency Injection patterns in Python (Real Python articles)
- Plugin discovery patterns (Python packaging user guide)
- Existing codebase structure and patterns
