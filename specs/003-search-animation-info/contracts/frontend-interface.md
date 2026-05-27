# Frontend Interface Contract: Search Animation Component

**Feature**: Informative Search Animation
**Date**: 2026-05-28
**Version**: 1.0

## Overview

This document defines the interface contract for the SearchAnimation component in the Second-Hand Search web application.

## Component Interface

### SearchAnimation Class

The animation component is implemented as a reusable JavaScript class.

**Constructor**:
```javascript
new SearchAnimation(container, options)
```

**Parameters**:
- `container` (HTMLElement | String, Required): DOM element or CSS selector for the animation container
- `options` (Object, Optional): Configuration options
  - `phases` (Array[PhaseConfig], Optional): Custom phase configurations (default: built-in phases)
  - `autoStart` (Boolean, Optional): Whether to start animation immediately (default: false)
  - `showProgressBar` (Boolean, Optional): Whether to show progress bar (default: true)
  - `showIcon` (Boolean, Optional): Whether to show phase icons (default: true)
  - `animationStyle` (String, Optional): Animation style preset ('chasing-dots', 'pulsing-ring', 'bouncing-bars') (default: 'chasing-dots')

**PhaseConfig Type**:
```typescript
interface PhaseConfig {
  id: string;           // Unique phase identifier
  label: string;       // Display text
  icon?: string;       // Icon name or SVG
  color?: string;      // Phase color (CSS color value)
  estimatedDurationMs?: number;  // For progress estimation
}
```

---

### Public Methods

#### `start(phases?)`
Starts the animation sequence.

**Parameters**:
- `phases` (Array[PhaseConfig], Optional): Override phases for this search

**Returns**: void

**Example**:
```javascript
animation.start();
// or with custom phases
animation.start([
  { id: 'custom1', label: 'Custom phase...' },
  { id: 'custom2', label: 'Another phase...' }
]);
```

---

#### `nextPhase(phaseId)`
Advances to the next phase in the sequence.

**Parameters**:
- `phaseId` (String, Required): The ID of the phase to transition to

**Returns**: void

**Behavior**:
- Updates the animation to reflect the new phase
- Updates the displayed message
- Recalculates progress percentage
- Triggers the phase transition animation

**Example**:
```javascript
animation.nextPhase('fetching');
```

---

#### `complete()`
Marks the search as complete and stops the animation.

**Parameters**: None

**Returns**: void

**Behavior**:
- Shows completion state
- Stops all animations
- Triggers completion callback if registered

---

#### `error(message)`
Puts the animation in an error state.

**Parameters**:
- `message` (String, Required): Error message to display

**Returns**: void

**Behavior**:
- Stops the loading animation
- Displays error message
- Applies error styling (typically red)
- Triggers error callback if registered

**Example**:
```javascript
animation.error('Failed to fetch listings. Please retry.');
```

---

#### `reset()`
Resets the animation to its initial state.

**Parameters**: None

**Returns**: void

**Behavior**:
- Returns to first phase
- Resets progress to 0
- Clears any error state
- Ready to start again

---

#### `setProgress(percentage)`
Manually sets the progress percentage.

**Parameters**:
- `percentage` (Number, Required): Progress value between 0 and 100

**Returns**: void

---

### Event Callbacks

The component supports the following event callbacks:

```javascript
// Register callbacks
animation.on('phaseChange', (phaseId, message) => {
  console.log(`Phase changed to: ${phaseId}`);
});

animation.on('complete', () => {
  console.log('Search completed!');
});

animation.on('error', (message) => {
  console.error(`Error: ${message}`);
});

animation.on('progress', (percentage) => {
  console.log(`Progress: ${percentage}%`);
});
```

**Supported Events**:
- `phaseChange`: Triggered when the phase changes
  - Payload: `{ phaseId: string, message: string, index: number }`
- `complete`: Triggered when the search completes
  - Payload: None
- `error`: Triggered when an error occurs
  - Payload: `{ message: string }`
- `progress`: Triggered when progress updates
  - Payload: `{ percentage: number }`

---

## HTML Structure

The component expects the following HTML structure in the container:

```html
<div id="search-animation-container">
  <!-- Component will insert its DOM here -->
</div>
```

**Minimum Requirements**:
- Container must have a defined width and height (or be sized by parent)
- Container should be visible (not `display: none`)
- Container should have `position: relative` or similar for proper positioning

---

## CSS Classes

The component adds the following CSS classes to the container:

- `.sa-container`: Main container class
- `.sa-animating`: Container is currently animating
- `.sa-error`: Container is in error state
- `.sa-complete`: Container has completed

**Scoped Classes** (prefixed with `.sa-`):
- `.sa-spinner`: The spinning/loading indicator
- `.sa-phase-text`: The phase message text
- `.sa-progress-bar`: The progress bar element
- `.sa-progress-fill`: The filled portion of the progress bar
- `.sa-icon`: The phase icon
- `.sa-dot`: Individual dots in chasing-dots animation
- `.sa-bar`: Individual bars in bouncing-bars animation

---

## Accessibility Contract

### ARIA Attributes

The component automatically manages the following ARIA attributes:

```html
<div 
  role="status"
  aria-live="polite"
  aria-atomic="true"
  aria-busy="true/false"
>
  <span aria-hidden="true">[visual animation]</span>
  <span class="sr-only">[status message]</span>
</div>
```

**Behavior**:
- `aria-live="polite"`: Screen readers announce status changes without interrupting
- `aria-atomic="true"`: Entire message is read as a unit
- `aria-busy`: Indicates loading state
- Visual animation elements have `aria-hidden="true"`
- Status text is always accessible to screen readers

### Reduced Motion Support

The component respects the `prefers-reduced-motion` media query:

```css
@media (prefers-reduced-motion: reduce) {
  .sa-spinner {
    animation: none;
  }
  /* Animation still shows static state with message */
}
```

---

## Integration Example

```html
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="/static/css/search-animation.css">
</head>
<body>
  <div id="search-container">
    <form id="search-form">
      <input type="text" id="search-input">
      <button type="submit">Search</button>
    </form>
    <div id="search-animation"></div>
    <div id="search-results"></div>
  </div>
  
  <script src="/static/js/search-animation.js"></script>
  <script>
    document.getElementById('search-form').addEventListener('submit', (e) => {
      e.preventDefault();
      const animation = new SearchAnimation('#search-animation', {
        animationStyle: 'chasing-dots',
        showProgressBar: true
      });
      
      animation.on('phaseChange', (data) => {
        console.log('Phase:', data.phaseId, data.message);
      });
      
      animation.start();
      
      // Simulate search phases
      setTimeout(() => animation.nextPhase('fetching'), 500);
      setTimeout(() => animation.nextPhase('filtering'), 2000);
      setTimeout(() => animation.complete(), 4000);
    });
  </script>
</body>
</html>
```

---

## File Locations

| File | Path | Purpose |
|------|------|---------|
| CSS | `/web/frontend/static/css/search-animation.css` | Animation styles |
| JS | `/web/frontend/static/js/search-animation.js` | Animation logic |
| Icons | `/web/frontend/static/images/loading/*.svg` | Optional custom icons |

---

## Version Compatibility

- **Initial Version**: 1.0
- **Backwards Compatible**: N/A (first version)
- **Breaking Changes**: None
