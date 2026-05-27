# Quickstart: Informative Search Animation

**Feature**: Informative Search Animation
**Date**: 2026-05-28
**Version**: 1.0

## Overview

This guide will help you quickly set up and test the Informative Search Animation feature for the Second-Hand Search web application.

## Prerequisites

- Python 3.11+ installed
- Node.js (optional, for development tooling)
- FastAPI running locally
- Web browser for testing

## Setup

### 1. Clone the Repository

```bash
cd C:\Users\bozhp\Projects\second_hand_searcher
```

### 2. Install Dependencies

```bash
# Create and activate virtual environment (if not already set up)
python -m venv venv
.\venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt  # If exists, or install from pyproject.toml
```

### 3. Start the Development Server

```bash
cd web\backend
uvicorn main:app --reload
```

The server will be available at: http://localhost:8000

## Development

### File Structure

```
second_hand_searcher/
├── web/
│   ├── backend/
│   │   └── api/
│   │       └── search.py          # Backend API (existing)
│   └── frontend/
│       ├── static/
│       │   ├── css/
│       │   │   └── search-animation.css  # NEW: Create this file
│       │   ├── js/
│       │   │   └── search-animation.js   # NEW: Create this file
│       │   └── images/
│       │       └── loading/              # NEW: Optional custom icons
│       └── templates/
│           └── index.html          # MODIFY: Add animation container
```

### 4. Create the Animation CSS

Create `web/frontend/static/css/search-animation.css`:

```css
/* Base styles - scoped with .sa- prefix */
.sa-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 4rem;
  padding: 1rem;
}

.sa-spinner {
  display: flex;
  gap: 0.5rem;
}

.sa-dot {
  width: 1rem;
  height: 1rem;
  background-color: #3b82f6;
  border-radius: 50%;
  animation: sa-bounce 1.4s infinite ease-in-out both;
}

.sa-dot:nth-child(1) { animation-delay: -0.32s; background-color: #3b82f6; }
.sa-dot:nth-child(2) { animation-delay: -0.16s; background-color: #8b5cf6; }
.sa-dot:nth-child(3) { animation-delay: 0s; background-color: #10b981; }

@keyframes sa-bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.sa-phase-text {
  font-size: 1rem;
  color: #374151;
  text-align: center;
  min-height: 1.5rem;
  transition: all 0.3s ease;
}

.sa-progress-bar {
  width: 100%;
  height: 4px;
  background-color: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.sa-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #10b981);
  border-radius: 2px;
  transition: width 0.3s ease, background-position 1s linear;
  width: 0%;
}

/* Error state */
.sa-error .sa-dot {
  background-color: #ef4444;
  animation: none;
}

.sa-error .sa-phase-text {
  color: #ef4444;
}

/* Complete state */
.sa-complete .sa-dot {
  background-color: #10b981;
  animation: sa-checkmark 0.5s ease-out forwards;
}

@keyframes sa-checkmark {
  0% { transform: scale(0); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .sa-dot {
    animation: none !important;
  }
  .sa-progress-fill {
    transition: none !important;
  }
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .sa-container {
    gap: 0.25rem;
    padding: 0.5rem;
  }
  .sa-dot {
    width: 0.75rem;
    height: 0.75rem;
  }
  .sa-phase-text {
    font-size: 0.875rem;
  }
}
```

### 5. Create the Animation JavaScript

Create `web/frontend/static/js/search-animation.js`:

```javascript
/**
 * SearchAnimation - Informative and fun search loading animation
 * 
 * Usage:
 * const animation = new SearchAnimation('#animation-container');
 * animation.start();
 * animation.nextPhase('fetching');
 * animation.complete();
 */

class SearchAnimation {
  /**
   * Default phase configurations for second-hand search
   */
  static DEFAULT_PHASES = [
    { id: 'initiating', label: 'Starting your search...', icon: 'search', color: '#3b82f6' },
    { id: 'fetching', label: 'Fetching listings from sources...', icon: 'database', color: '#8b5cf6' },
    { id: 'filtering', label: 'Applying your filters...', icon: 'filter', color: '#f59e0b' },
    { id: 'ranking', label: 'Ranking results by relevance...', icon: 'trophy', color: '#10b981' },
    { id: 'loading', label: 'Loading results...', icon: 'loader', color: '#06b6d4' },
    { id: 'complete', label: 'Done!', icon: 'check', color: '#10b981' }
  ];

  /**
   * Fun messages for long searches (easter eggs)
   */
  static FUN_MESSAGES = [
    'Hunting for deals...',
    'Scouring the web for you...',
    'Finding hidden gems...',
    'On the prowl for bargains...',
    'Searching far and wide...'
  ];

  constructor(container, options = {}) {
    this.container = typeof container === 'string' 
      ? document.querySelector(container)
      : container;
    
    if (!this.container) {
      throw new Error('SearchAnimation: Container element not found');
    }

    this.options = {
      phases: options.phases || SearchAnimation.DEFAULT_PHASES,
      autoStart: options.autoStart || false,
      showProgressBar: options.showProgressBar !== false,
      showIcon: options.showIcon !== false,
      animationStyle: options.animationStyle || 'chasing-dots'
    };

    this.currentPhaseIndex = 0;
    this.isAnimating = false;
    this.isError = false;
    this.startTime = null;
    this.eventListeners = {};

    this.init();
    
    if (this.options.autoStart) {
      this.start();
    }
  }

  /**
   * Initialize DOM structure
   */
  init() {
    this.container.classList.add('sa-container');
    
    // Create spinner container
    this.spinner = document.createElement('div');
    this.spinner.className = 'sa-spinner';
    this.container.appendChild(this.spinner);

    // Create dots for chasing animation
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'sa-dot';
      this.spinner.appendChild(dot);
    }

    // Create phase text
    this.phaseText = document.createElement('div');
    this.phaseText.className = 'sa-phase-text';
    this.phaseText.setAttribute('aria-live', 'polite');
    this.phaseText.setAttribute('aria-atomic', 'true');
    this.container.appendChild(this.phaseText);

    // Create progress bar
    if (this.options.showProgressBar) {
      this.progressBar = document.createElement('div');
      this.progressBar.className = 'sa-progress-bar';
      
      this.progressFill = document.createElement('div');
      this.progressFill.className = 'sa-progress-fill';
      this.progressBar.appendChild(this.progressFill);
      
      this.container.appendChild(this.progressBar);
    }

    // Set ARIA role
    this.container.setAttribute('role', 'status');
    this.container.setAttribute('aria-busy', 'false');
  }

  /**
   * Start the animation
   */
  start(phases) {
    if (phases) {
      this.options.phases = phases;
    }

    this.currentPhaseIndex = 0;
    this.isAnimating = true;
    this.isError = false;
    this.startTime = Date.now();
    this.container.classList.add('sa-animating');
    this.container.classList.remove('sa-error', 'sa-complete');
    this.container.setAttribute('aria-busy', 'true');

    this.updatePhase();
    this.emit('phaseChange', this.getPhaseEventData());
  }

  /**
   * Advance to next phase
   */
  nextPhase(phaseId) {
    const phaseIndex = this.options.phases.findIndex(p => p.id === phaseId);
    if (phaseIndex >= 0) {
      this.currentPhaseIndex = phaseIndex;
      this.updatePhase();
      this.emit('phaseChange', this.getPhaseEventData());
    }
  }

  /**
   * Update current phase display
   */
  updatePhase() {
    const phase = this.options.phases[this.currentPhaseIndex];
    
    // Sometimes show fun messages for long-running searches
    if (this.currentPhaseIndex === 1 && this.options.phases.length > 3) {
      const randomIndex = Math.floor(Math.random() * 10);
      if (randomIndex === 0) {
        const funMessage = SearchAnimation.FUN_MESSAGES[
          Math.floor(Math.random() * SearchAnimation.FUN_MESSAGES.length)
        ];
        this.phaseText.textContent = funMessage;
      } else {
        this.phaseText.textContent = phase.label;
      }
    } else {
      this.phaseText.textContent = phase.label;
    }

    // Update progress
    if (this.options.showProgressBar) {
      const progress = ((this.currentPhaseIndex + 1) / this.options.phases.length) * 100;
      this.progressFill.style.width = `${Math.min(progress, 100)}%`;
      this.emit('progress', { percentage: progress });
    }

    // Update colors if defined
    if (phase.color) {
      const dots = this.spinner.querySelectorAll('.sa-dot');
      dots.forEach((dot, index) => {
        const colors = phase.color.split(',').map(c => c.trim()) || [phase.color];
        dot.style.backgroundColor = colors[index % colors.length];
      });
    }
  }

  /**
   * Mark search as complete
   */
  complete() {
    this.isAnimating = false;
    this.container.classList.remove('sa-animating');
    this.container.classList.add('sa-complete');
    this.container.setAttribute('aria-busy', 'false');
    
    // Go to final phase
    this.currentPhaseIndex = this.options.phases.length - 1;
    this.updatePhase();
    
    this.emit('complete');
  }

  /**
   * Show error state
   */
  error(message) {
    this.isAnimating = false;
    this.isError = true;
    this.container.classList.remove('sa-animating', 'sa-complete');
    this.container.classList.add('sa-error');
    this.container.setAttribute('aria-busy', 'false');
    
    this.phaseText.textContent = message;
    this.emit('error', { message });
  }

  /**
   * Reset animation
   */
  reset() {
    this.isAnimating = false;
    this.isError = false;
    this.container.classList.remove('sa-animating', 'sa-error', 'sa-complete');
    this.container.setAttribute('aria-busy', 'false');
    
    if (this.options.showProgressBar) {
      this.progressFill.style.width = '0%';
    }
    
    this.currentPhaseIndex = 0;
    this.phaseText.textContent = '';
  }

  /**
   * Set manual progress
   */
  setProgress(percentage) {
    if (this.options.showProgressBar) {
      this.progressFill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
    }
  }

  /**
   * Event listener management
   */
  on(event, callback) {
    if (!this.eventListeners[event]) {
      this.eventListeners[event] = [];
    }
    this.eventListeners[event].push(callback);
  }

  emit(event, data) {
    if (this.eventListeners[event]) {
      this.eventListeners[event].forEach(callback => callback(data));
    }
  }

  getPhaseEventData() {
    const phase = this.options.phases[this.currentPhaseIndex];
    return {
      phaseId: phase.id,
      message: this.phaseText.textContent,
      index: this.currentPhaseIndex
    };
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SearchAnimation;
}
```

### 6. Modify the HTML Template

Update `web/frontend/templates/index.html` to include the animation:

```html
<!-- Add to the <head> section -->
<link rel="stylesheet" href="/static/css/search-animation.css">

<!-- In the search section, add a container for the animation -->
<div class="search-container">
  <form id="search-form">
    <input type="text" id="search-query" placeholder="Search for products..." required>
    <button type="submit">Search</button>
  </form>
  
  <!-- Animation will appear here during search -->
  <div id="search-animation"></div>
  
  <div id="search-results"></div>
</div>

<!-- Add at the end of <body> -->
<script src="/static/js/search-animation.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchAnimation = new SearchAnimation('#search-animation', {
      animationStyle: 'chasing-dots',
      showProgressBar: true,
      showIcon: true
    });

    searchForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      // Start animation
      searchAnimation.start();
      
      // Get search query
      const query = document.getElementById('search-query').value;
      
      // Simulate search with phase transitions
      // In production, this would be replaced with actual API calls
      simulateSearch(query, searchAnimation);
    });

    function simulateSearch(query, animation) {
      // Simulate different phases
      setTimeout(() => animation.nextPhase('fetching'), 500);
      setTimeout(() => animation.nextPhase('filtering'), 1500);
      setTimeout(() => animation.nextPhase('ranking'), 2500);
      setTimeout(() => animation.nextPhase('loading'), 3000);
      setTimeout(() => {
        animation.complete();
        // In production: display actual results
        displayMockResults(query);
      }, 4000);
    }

    function displayMockResults(query) {
      const resultsDiv = document.getElementById('search-results');
      resultsDiv.innerHTML = `<h3>Results for: ${query}</h3><p>Mock results displayed</p>`;
    }
  });
</script>
```

## Testing

### Manual Testing

1. Open your browser to http://localhost:8000
2. Enter a search query and submit the form
3. Verify that:
   - The chasing dots animation appears
   - Status text updates through each phase
   - Progress bar fills up
   - Animation completes and shows "Done!"
   - Occasionally see fun messages like "Hunting for deals..."

### Visual Testing

- **Desktop**: Animation should be smooth at 60 FPS
- **Mobile**: Animation should adapt to smaller screens
- **Reduced Motion**: Test with `prefers-reduced-motion: reduce` in browser dev tools

### Accessibility Testing

1. Use a screen reader to verify status messages are announced
2. Verify keyboard navigation works
3. Check color contrast ratios
4. Test with various zoom levels

## Debugging

### Common Issues

**Animation doesn't appear**:
- Check that the CSS and JS files are properly linked
- Verify the container element exists in the DOM
- Check browser console for errors

**Animation is choppy**:
- Ensure you're using GPU-accelerated properties (transform, opacity)
- Check if reduced motion is enabled in the browser

**Status text doesn't update**:
- Verify phase configurations are correct
- Check that the animation is in `sa-animating` state

## Performance Tips

1. Use Chrome DevTools to check FPS
2. Profile animation performance
3. Test on low-powered devices
4. Consider simplifying animations if performance is poor

## Next Steps

After implementing the basic animation:

1. Connect to real backend search API
2. Add error handling for failed searches
3. Implement cancel/abort functionality
4. Add more animation styles (pulsing ring, bouncing bars)
5. Customize colors to match your brand
