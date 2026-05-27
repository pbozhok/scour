# Data Model: Informative Search Animation

**Feature**: Informative Search Animation
**Date**: 2026-05-28
**Version**: 1.0

## Entities

### Entity 1: SearchPhase

Represents a distinct stage in the search process.

**Fields**:
- `id` (String, Required): Unique identifier for the phase (e.g., "initiating", "fetching", "filtering")
- `label` (String, Required): Human-readable label for display (e.g., "Starting your search...")
- `description` (String, Optional): Detailed description of what happens in this phase
- `estimatedDurationMs` (Integer, Optional): Typical duration in milliseconds (for progress estimation)
- `icon` (String, Optional): SVG icon name or path to display for this phase
- `color` (String, Optional): Primary color associated with this phase (hex or CSS color name)
- `order` (Integer, Required): Sequential order in the search pipeline

**Validation Rules**:
- `id` must be unique across all phases
- `label` must be non-empty and less than 100 characters
- `order` must be a positive integer
- `estimatedDurationMs` must be >= 0 if provided

**State Transitions**:
- Phases progress sequentially from lower `order` to higher `order`
- A phase can transition to any subsequent phase (skipping is allowed)
- No backward transitions (phases only move forward)

**Example**:
```json
{
  "id": "fetching",
  "label": "Fetching listings from sources...",
  "description": "Retrieving product data from scraper modules",
  "estimatedDurationMs": 2000,
  "icon": "database",
  "color": "#3b82f6",
  "order": 2
}
```

---

### Entity 2: AnimationState

Represents the current visual and textual state of the animation component.

**Fields**:
- `currentPhaseId` (String, Required): ID of the currently active phase
- `message` (String, Required): The status message currently displayed
- `progress` (Float, Optional): Estimated progress percentage (0-100)
- `isAnimating` (Boolean, Required): Whether animation is currently running
- `isError` (Boolean, Required): Whether the animation is in an error state
- `errorMessage` (String, Optional): Error message to display if `isError` is true
- `timestamp` (Integer, Required): Unix timestamp when this state was set

**Validation Rules**:
- `currentPhaseId` must match an existing SearchPhase.id
- `progress` must be between 0 and 100 if provided
- `message` must be non-empty
- If `isError` is true, `errorMessage` must be provided

**State Transitions**:
- `isAnimating`: true when search starts, false when search completes or errors
- `currentPhaseId`: Updates as search progresses through phases
- `progress`: Increments as phases complete
- `isError`: Becomes true when an error occurs, can reset to false on retry

**Example**:
```json
{
  "currentPhaseId": "filtering",
  "message": "Applying your filters...",
  "progress": 65.0,
  "isAnimating": true,
  "isError": false,
  "timestamp": 1716892800
}
```

---

### Entity 3: ProgressInformation

Collection of all status messages and contextual data displayed during a search operation.

**Fields**:
- `searchId` (String, Required): Unique identifier for the search session
- `phases` (Array[SearchPhase], Required): All phases that will/may occur in this search
- `currentState` (AnimationState, Required): The current animation state
- `phaseHistory` (Array[AnimationState], Required): History of all states during this search
- `startTime` (Integer, Required): Unix timestamp when search started
- `endTime` (Integer, Optional): Unix timestamp when search completed

**Validation Rules**:
- `searchId` must be unique for each search
- `phases` must be non-empty and ordered by `order` field
- `phaseHistory` must contain the initial state
- Each state in `phaseHistory` must have a `timestamp` >= previous state's timestamp

**Relationships**:
- ProgressInformation contains multiple SearchPhase entities
- ProgressInformation contains multiple AnimationState entities
- AnimationState references a single SearchPhase

**Example**:
```json
{
  "searchId": "search_abc123",
  "phases": [
    {"id": "initiating", "label": "Starting your search...", "order": 1},
    {"id": "fetching", "label": "Fetching listings...", "order": 2},
    {"id": "filtering", "label": "Applying filters...", "order": 3}
  ],
  "currentState": {
    "currentPhaseId": "fetching",
    "message": "Fetching listings...",
    "progress": 40.0,
    "isAnimating": true,
    "isError": false,
    "timestamp": 1716892805
  },
  "phaseHistory": [...],
  "startTime": 1716892800
}
```

## Data Flow

1. **Search Initiation**: User submits search → AnimationState created with first phase
2. **Phase Transition**: Backend completes a phase → AnimationState updated with new phase
3. **Progress Update**: Time passes or backend notifies → ProgressInformation.progress updated
4. **Search Completion**: All phases complete → AnimationState.isAnimating = false
5. **Error Handling**: Error occurs → AnimationState.isError = true, errorMessage set

## Storage Requirements

- **Client-side only**: All data is stored in JavaScript memory during the search
- **No persistence**: Data is not saved to backend or localStorage
- **Session-scoped**: Each search has its own isolated ProgressInformation

## Validation Summary

| Entity | Required Fields | Optional Fields | Constraints |
|--------|----------------|-----------------|-------------|
| SearchPhase | id, label, order | description, estimatedDurationMs, icon, color | id unique, order > 0 |
| AnimationState | currentPhaseId, message, isAnimating, isError, timestamp | progress, errorMessage | progress 0-100, errorMessage required if isError |
| ProgressInformation | searchId, phases, currentState, phaseHistory, startTime | endTime | searchId unique, phases ordered |
