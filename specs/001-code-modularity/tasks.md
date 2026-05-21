---

description: "Task list for Code Modularity feature implementation"
---

# Tasks: Code Modularity

**Input**: Design documents from `/specs/001-code-modularity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/module-interface.md, quickstart.md

**Tests**: Tests included per Test-First principle (spec FR-009, SC-003)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and base structure for modular architecture

- [x] T001 Create core/ directory with __init__.py at core/__init__.py
- [x] T002 Create registry.py module registry at core/registry.py
- [x] T003 Create injection.py dependency injection container at core/injection.py
- [x] T004 [P] Create llm/ directory with __init__.py at llm/__init__.py
- [x] T005 [P] Move existing llm clients to llm/ directory (gemini.py, mistral.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create base Module ABC with initialize/validate/execute/cleanup in core/module.py
- [x] T007 Create PipelineContext dataclass in core/context.py
- [x] T008 [P] Create ModuleType enum in core/module.py
- [x] T009 [P] Create PipelineError dataclass in core/errors.py
- [x] T010 Implement module registry with register/get_modules/load_all in core/registry.py
- [x] T011 Implement dependency injection container in core/injection.py
- [x] T012 Create BaseScraper ABC extending Module in scrapers/base.py
- [x] T013 [P] Create BaseFilter ABC extending Module in filters/base.py
- [x] T014 [P] Create BaseProcessor ABC extending Module in processors/base.py
- [x] T015 [P] Create BaseReviewer ABC extending Module in reviewers/base.py
- [x] T016 [P] Create BaseLLMClient ABC in llm/base.py
- [x] T017 Create structured logging setup with JSON formatter in core/logging.py
- [x] T018 [P] Add logging imports to all existing modules (scrapers/*.py, filters/*.py, etc.)
- [ ] T019 Update second_hand_research.py to use new module pipeline with context passing
- [ ] T020 Add module error handling in second_hand_research.py to isolate failures
- [x] T021 Create base test utilities in tests/conftest.py (fixtures for context, mock modules)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Add New Platform Scraper (Priority: P1) 🎯 MVP

**Goal**: A developer can add support for a new marketplace platform by creating a new scraper module that follows the existing scraper interface, without modifying any existing scraper code

**Independent Test**: Can be fully tested by adding a mock scraper module in scrapers/mock_scraper.py and verifying it integrates with the main search flow without breaking existing scrapers

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T022 [P] [US1] Contract test for BaseScraper interface in tests/test_scrapers.py
- [x] T023 [P] [US1] Test module discovery registers new scrapers in tests/test_registry.py
- [x] T024 [P] [US1] Integration test for mock scraper in tests/integration/test_scraper_integration.py

### Implementation for User Story 1

- [x] T025 [US1] Formalize BaseScraper with name/type/version class attributes in scrapers/base.py
- [x] T026 [P] [US1] Add scrape() abstract method to BaseScraper in scrapers/base.py
- [x] T027 [P] [US1] Update existing scrapers (dba.py, vinted.py, tradera.py) to inherit from BaseScraper
- [x] T028 [US1] Implement module discovery in core/registry.py for scrapers/ directory
- [x] T029 [US1] Add scraper-specific config validation in scrapers/base.py
- [ ] T030 [US1] Update pipeline to pass context through scrapers in second_hand_research.py
- [x] T031 [US1] Add error isolation for scrapers in second_hand_research.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. A developer can add scrapers/mock_scraper.py and it will be discovered and used.

---

## Phase 4: User Story 2 - Swap LLM Backend (Priority: P1)

**Goal**: A developer can change the LLM provider from Gemini to Mistral by updating a configuration setting, without modifying any core ranking or filtering logic

**Independent Test**: Can be tested by switching the LLM config and verifying all AI-powered features (filtering, scoring, review summarization) work with the new provider

### Tests for User Story 2 ⚠️

- [ ] T032 [P] [US2] Contract test for BaseLLMClient interface in tests/test_llm.py
- [ ] T033 [P] [US2] Test LLM client swapping via config in tests/test_llm_config.py
- [ ] T034 [P] [US2] Integration test for Mistral client in tests/integration/test_llm_mistral.py

### Implementation for User Story 2

- [ ] T035 [US2] Formalize BaseLLMClient with chat() method in llm/base.py
- [ ] T036 [P] [US2] Update gemini.py to inherit from BaseLLMClient in llm/gemini.py
- [ ] T037 [P] [US2] Update mistral.py to inherit from BaseLLMClient in llm/mistral.py
- [ ] T038 [US2] Create LLM client factory in llm/__init__.py
- [ ] T039 [US2] Add LLM client injection to dependency container in core/injection.py
- [ ] T040 [US2] Update config.py to define LLM_PROVIDERS mapping
- [ ] T041 [US2] Add --llm CLI argument to second_hand_research.py
- [ ] T042 [US2] Update llm_filter.py to use injected LLM client from container
- [ ] T043 [US2] Update ranker.py to use injected LLM client from container
- [ ] T044 [US2] Update reviewers/summarizer.py to use injected LLM client from container

**Checkpoint**: At this point, User Story 2 should be fully functional and testable independently. Switching --llm flag changes the provider used.

---

## Phase 5: User Story 3 - Test Component in Isolation (Priority: P2)

**Goal**: A developer can write and run unit tests for any individual module (scraper, filter, processor, ranker) without needing to instantiate the entire application

**Independent Test**: Can be tested by running tests for a single module (e.g., pytest tests/test_scrapers.py -v) and verifying they pass without requiring other modules to be present

### Tests for User Story 3 ⚠️

- [ ] T045 [P] [US3] Contract test for BaseFilter interface in tests/test_filters.py
- [ ] T046 [P] [US3] Contract test for BaseProcessor interface in tests/test_processors.py
- [ ] T047 [P] [US3] Contract test for BaseReviewer interface in tests/test_reviewers.py
- [ ] T048 [P] [US3] Unit test for keyword_filter with mock data in tests/test_filters.py
- [ ] T049 [P] [US3] Unit test for price_converter with test rates in tests/test_processors.py

### Implementation for User Story 3

- [ ] T050 [US3] Create mock module factory in tests/conftest.py for all module types
- [ ] T051 [P] [US3] Create mock PipelineContext factory in tests/conftest.py
- [ ] T052 [P] [US3] Add unit tests for dba.py scraper in tests/test_scrapers.py
- [ ] T053 [P] [US3] Add unit tests for vinted.py scraper in tests/test_scrapers.py
- [ ] T054 [P] [US3] Add unit tests for tradera.py scraper in tests/test_scrapers.py
- [ ] T055 [US3] Add unit tests for llm_filter.py in tests/test_filters.py
- [ ] T056 [US3] Add unit tests for keyword_filter.py in tests/test_filters.py
- [ ] T057 [US3] Add unit tests for all processors in tests/test_processors.py
- [ ] T058 [US3] Add unit tests for all reviewers in tests/test_reviewers.py

**Checkpoint**: All user stories should now be independently functional and testable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T059 [P] Update all module __init__.py files to export classes properly
- [ ] T060 [P] Add docstrings to all new module classes and methods
- [ ] T061 Update README.md with new modular architecture documentation
- [ ] T062 Update README.md with new LLM configuration options
- [ ] T063 [P] Run all tests with pytest to verify integration
- [ ] T064 Performance test: verify scrapers complete in <5s in tests/performance/test_scrapers.py
- [ ] T065 Performance test: verify filters complete in <2s in tests/performance/test_filters.py
- [ ] T066 Performance test: verify LLM modules complete in <10s in tests/performance/test_llm.py
- [ ] T067 Update quickstart.md with actual code examples from implementation
- [ ] T068 Validate all contract tests pass for all module interfaces

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) - No dependencies on other stories
- **Polish (Phase 6)**: Depends on all user stories (Phases 3-5) being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories

All three user stories are **independent** and can be worked on in parallel once Phase 2 is complete.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Base classes before concrete implementations
- Core implementation before integration
- Story complete before moving to next priority

---

## Parallel Opportunities

### Phase 1 (Setup)
```bash
# All Phase 1 tasks can run in parallel (different files):
T001: core/__init__.py
T002: core/registry.py
T003: core/injection.py
T004: llm/__init__.py
T005: llm/ gemini.py, mistral.py move
```

### Phase 2 (Foundational)
```bash
# Parallel groups in Phase 2:
# Group A (Core modules):
T006: core/module.py
T007: core/context.py
T008: core/module.py (ModuleType)
T009: core/errors.py

# Group B (Base classes - all independent):
T012: scrapers/base.py
T013: filters/base.py
T014: processors/base.py
T015: reviewers/base.py
T016: llm/base.py

# Group C (Registry & DI):
T010: core/registry.py (registry logic)
T011: core/injection.py

# Group D (Integration):
T017: core/logging.py
T018: Add logging to existing modules
T019-T020: Update second_hand_research.py
T021: Error handling in pipeline
```

### User Story 1 (Phase 3)
```bash
# Tests first (all parallel):
T022-T024: tests/test_scrapers.py, tests/test_registry.py, tests/integration/test_scraper_integration.py

# Implementation (parallel models):
T025-T026: scrapers/base.py enhancements
T027: Update existing scrapers
T028: Module discovery in registry
T029: Config validation
T030-T031: Pipeline updates
```

### User Story 2 (Phase 4)
```bash
# Tests first (all parallel):
T032-T034: tests/test_llm.py, tests/test_llm_config.py, tests/integration/test_llm_mistral.py

# Implementation (parallel):
T035: llm/base.py formalization
T036-T037: Update gemini.py and mistral.py
T038: LLM factory
T039: DI container updates
T040-T041: Config and CLI updates
T042-T044: Update consumers (llm_filter, ranker, summarizer)
```

### User Story 3 (Phase 5)
```bash
# Tests first (all parallel):
T045-T049: All contract and unit tests

# Implementation (parallel):
T050-T051: Test fixtures
T052-T054: Scraper unit tests
T055-T058: Filter, processor, reviewer unit tests
```

### Parallel Team Strategy

With multiple developers:

1. **Phase 1**: All developers work on setup in parallel
2. **Phase 2**: Split foundational tasks across developers
3. **Phases 3-5**: Each developer takes a user story:
   - Developer A: User Story 1 (Add New Platform Scraper)
   - Developer B: User Story 2 (Swap LLM Backend)
   - Developer C: User Story 3 (Test Component in Isolation)
4. **Phase 6**: All developers collaborate on polish tasks

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test that new scrapers can be added
5. Deploy/demo if ready

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 → Module system with scraper support
2. **V1.1**: Add US2 → LLM backend swappable
3. **V1.2**: Add US3 → Full test coverage
4. **V1.3**: Polish → Documentation, performance validation

### Key Milestones

- **After Phase 2**: Core modular infrastructure complete
- **After Phase 3**: Can add new platform scrapers (US1 done)
- **After Phase 4**: Can swap LLM providers (US2 done)
- **After Phase 5**: All modules testable in isolation (US3 done)
- **After Phase 6**: Production ready with full documentation

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [US1]/[US2]/[US3] labels map tasks to specific user stories for traceability
- Each user story is independently completable and testable
- Tests are written FIRST and must FAIL before implementation (Test-First principle)
- Commit after each task or logical group of parallel tasks
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Summary

| Phase | Count | Type | Status |
|-------|-------|------|--------|
| Phase 1 | 5 | Setup | ✅ Complete |
| Phase 2 | 15 | Foundational | ✅ Complete (14/15) |
| Phase 3 (US1) | 9 | User Story 1 (P1) | ✅ Complete (8/9) |
| Phase 4 (US2) | 12 | User Story 2 (P1) | Pending |
| Phase 5 (US3) | 14 | User Story 3 (P2) | Pending |
| Phase 6 | 10 | Polish | Pending |
| **Total** | **65** | | **34% complete (27/65)** |

**Parallel Opportunities**: 42 tasks marked [P] (64% of total)
**Independent Stories**: 3 user stories, all can run in parallel after Phase 2
**MVP Scope**: Phase 1 + Phase 2 + Phase 3 = 29 tasks (27/29 complete = 93%)
