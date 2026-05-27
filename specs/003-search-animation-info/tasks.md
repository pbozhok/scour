---

description: "Task list for Informative Search Animation feature implementation"
---

# Tasks: Informative Search Animation

**Input**: Design documents from `/specs/003-search-animation-info/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in feature specification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `web/backend/`, `web/frontend/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for search animation feature

- [ ] T001 Create search animation CSS file at web/frontend/static/css/search-animation.css
- [ ] T002 Create search animation JS file at web/frontend/static/js/search-animation.js
- [ ] T003 [P] Create loading icons directory at web/frontend/static/images/loading/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Create backend SSE endpoint for search phase updates in web/backend/api/search_sse.py
- [ ] T005 [P] Modify search service to emit phase transition events in web/backend/services/search.py
- [ ] T006 [P] Add SSE dependency to FastAPI backend (sse-starlette or equivalent)
- [ ] T007 Create SearchAnimation JavaScript class in web/frontend/static/js/search-animation.js
- [ ] T008 [P] Create base CSS animations in web/frontend/static/css/search-animation.css
- [ ] T009 Add fun facts static list to web/frontend/static/js/search-animation.js

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Search Progress Information (Priority: P1) 🎯 MVP

**Goal**: Users see animation that clearly communicates what background processes are currently happening during search

**Independent Test**: Initiate a search and verify animation displays meaningful status updates throughout the search process

### Implementation for User Story 1

- [ ] T010 [P] [US1] Add animation container to web/frontend/templates/index.html
- [ ] T011 [P] [US1] Implement chasing-dots animation CSS in web/frontend/static/css/search-animation.css
- [ ] T012 [US1] Implement start() method in SearchAnimation class in web/frontend/static/js/search-animation.js
- [ ] T013 [US1] Implement nextPhase() method in SearchAnimation class in web/frontend/static/js/search-animation.js
- [ ] T014 [US1] Implement complete() method in SearchAnimation class in web/frontend/static/js/search-animation.js
- [ ] T015 [US1] Implement error() method in SearchAnimation class in web/frontend/static/js/search-animation.js
- [ ] T016 [US1] Implement reset() method in SearchAnimation class in web/frontend/static/js/search-animation.js
- [ ] T017 [US1] Connect frontend to SSE endpoint for phase updates in web/frontend/static/js/search-animation.js
- [ ] T018 [US1] Add default phase configurations to SearchAnimation class
- [ ] T019 [US1] Handle SSE connection errors with fallback to client-side estimation

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Animation displays and updates through search phases via SSE.

---

## Phase 4: User Story 2 - Understand Search Phase Details (Priority: P2)

**Goal**: Users can understand specific phases of the search process and see visual progress indicators

**Independent Test**: Initiate a multi-phase search and verify each phase is clearly labeled with progress indication

### Implementation for User Story 2

- [ ] T020 [P] [US2] Add progress bar CSS styles in web/frontend/static/css/search-animation.css
- [ ] T021 [P] [US2] Implement progress bar HTML structure in SearchAnimation class
- [ ] T022 [US2] Implement setProgress() method in SearchAnimation class in web/frontend/static/js/search-animation.js
- [ ] T023 [US2] Add phase icons (SVG) to web/frontend/static/images/loading/ (search.svg, database.svg, filter.svg, trophy.svg, loader.svg, check.svg)
- [ ] T024 [P] [US2] Implement icon display logic in SearchAnimation class
- [ ] T025 [US2] Add phase-specific colors to CSS animations in web/frontend/static/css/search-animation.css
- [ ] T026 [US2] Implement smooth color transitions between phases in web/frontend/static/css/search-animation.css
- [ ] T027 [US2] Add estimated phase durations to SearchAnimation configuration
- [ ] T028 [US2] Implement micro-interaction animations (bounce, fade) in web/frontend/static/css/search-animation.css

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Animation is visually engaging with phase details and progress indicators.

---

## Phase 5: User Story 3 - Accessible Progress Feedback (Priority: P2)

**Goal**: Users with visual impairments or using screen readers receive the same progress information through accessible means

**Independent Test**: Use screen reader to verify status changes are announced; test with prefers-reduced-motion

### Implementation for User Story 3

- [ ] T029 [P] [US3] Add ARIA attributes to animation container in SearchAnimation class
- [ ] T030 [P] [US3] Add role="status" and aria-live="polite" to animation elements
- [ ] T031 [US3] Add aria-busy attribute management in SearchAnimation class
- [ ] T032 [US3] Create .sr-only CSS class for screen reader only text in web/frontend/static/css/search-animation.css
- [ ] T033 [US3] Add prefers-reduced-motion media query support in web/frontend/static/css/search-animation.css
- [ ] T034 [US3] Add hidden text for screen readers with phase messages in SearchAnimation class
- [ ] T035 [US3] Test animation with keyboard navigation in web/frontend/templates/index.html

**Checkpoint**: All user stories should now be independently functional. Animation is accessible to all users.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T036 [P] Add optional animation styles (pulsing-ring, bouncing-bars) to SearchAnimation class
- [ ] T037 [P] Add configuration options to SearchAnimation constructor (showProgressBar, showIcon, animationStyle)
- [ ] T038 [P] Implement event callback system (phaseChange, complete, error, progress) in SearchAnimation class
- [ ] T039 [P] Add auto-reconnect logic for SSE connection in web/frontend/static/js/search-animation.js
- [ ] T040 [P] Create responsive CSS adjustments for mobile in web/frontend/static/css/search-animation.css
- [ ] T041 Validate with quickstart.md test scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Enhances US1 but independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Enhances US1/US2 but independently testable

### Within Each User Story

- Core infrastructure (Setup + Foundational) before user story work
- Implementation tasks in logical order
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel
- All US2 tasks marked [P] can run in parallel
- All US3 tasks marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 2

```bash
# Launch all parallel tasks for User Story 2 together:
Task: "Add progress bar CSS styles in web/frontend/static/css/search-animation.css"
Task: "Implement progress bar HTML structure in SearchAnimation class"
Task: "Implement setProgress() method in SearchAnimation class"
Task: "Add phase icons (SVG) to web/frontend/static/images/loading/"
Task: "Add phase-specific colors to CSS animations"
```

---

## Parallel Example: User Story 3

```bash
# Launch all parallel tasks for User Story 3 together:
Task: "Add ARIA attributes to animation container"
Task: "Add role=status and aria-live=polite to animation elements"
Task: "Create .sr-only CSS class for screen reader only text"
Task: "Add prefers-reduced-motion media query support"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

**MVP Deliverables**: Basic animation with SSE phase updates, no progress bar, no icons, no accessibility enhancements

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (enhanced UI)
4. Add User Story 3 → Test independently → Deploy/Demo (accessible)
5. Add Polish phase → Full feature complete

Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (core functionality)
   - Developer B: User Story 2 (visual enhancements)
   - Developer C: User Story 3 (accessibility)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Fun facts are randomly selected from static list during fetch phase
- SSE connection automatically manages phase updates from backend
- Animation gracefully falls back to client-side estimation if SSE connection drops
