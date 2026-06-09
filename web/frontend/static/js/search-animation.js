/**
 * SearchAnimation - Informative and fun search loading animation
 * 
 * Provides real-time progress updates via SSE connection to backend
 * Falls back to client-side estimation if SSE connection is lost
 * 
 * Usage:
 * const animation = new SearchAnimation('#animation-container');
 * animation.start();
 * animation.nextPhase('fetching');
 * animation.complete();
 */

class SearchAnimation {
  /**
   * Default phase configurations for second-hand search pipeline
   * Maps to backend pipeline: scrapers → filters → processors → rankers
   */
  static DEFAULT_PHASES = [
    { id: 'initiating', label: 'Starting your search...', icon: 'search', color: '#3b82f6', order: 1, estimatedDurationMs: 500 },
    { id: 'fetching', label: 'Fetching listings from sources...', icon: 'database', color: '#8b5cf6', order: 2, estimatedDurationMs: 3000 },
    { id: 'filtering', label: 'Applying your filters...', icon: 'filter', color: '#f59e0b', order: 3, estimatedDurationMs: 2000 },
    { id: 'ranking', label: 'Ranking results by relevance...', icon: 'trophy', color: '#06b6d4', order: 4, estimatedDurationMs: 1500 },
    { id: 'loading', label: 'Loading results...', icon: 'loader', color: '#10b981', order: 5, estimatedDurationMs: 1000 },
    { id: 'complete', label: 'Done!', icon: 'check', color: '#10b981', order: 6, estimatedDurationMs: 0 }
  ];

  static FUN_MESSAGES = [
    'Hunting for deals...',
    'Scouring the web for you...',
    'Finding hidden gems...',
    'On the prowl for bargains...',
    'Searching far and wide...',
    'Did you know? Second-hand items reduce waste by 80% on average.',
    'Fun fact: The average person saves $1,500 per year by buying second-hand.',
    'Interesting: Second-hand shopping reduces carbon footprint by 30%.',
    'Fact: 70% of second-hand items are in excellent condition.',
    'Tip: Buying second-hand helps support local communities.'
  ];

  eventSource = null;

  constructor(container, options = {}) {
    // Handle container selector or element
    this.container = typeof container === 'string'
      ? document.querySelector(container)
      : container;

    if (!this.container) {
      throw new Error('SearchAnimation: Container element not found');
    }

    // Merge options with defaults
    this.options = {
      phases: options.phases || SearchAnimation.DEFAULT_PHASES,
      autoStart: options.autoStart || false,
      showProgressBar: options.showProgressBar !== false,
      showIcon: options.showIcon !== false,
      animationStyle: options.animationStyle || 'chasing-dots',
      sseEndpoint: options.sseEndpoint || '/api/v1/search/phases',
      iconPath: options.iconPath || '/static/images/loading'
    };

    // State management
    this.currentPhaseIndex = 0;
    this.isAnimating = false;
    this.isError = false;
    this.sseConnected = false;
    this.startTime = null;
    this.eventListeners = {};
    this.phaseTimer = null;

    // DOM elements (created in init)
    this.spinner = null;
    this.phaseText = null;
    this.progressBar = null;
    this.progressFill = null;
    this.phaseIcon = null;
    this.srText = null;

    // Initialize DOM
    this.init();

    // Auto-start if configured
    if (this.options.autoStart) {
      this.start();
    }
  }

  /**
   * Initialize DOM structure for animation component
   */
  init() {
    // Add base container class
    this.container.classList.add('sa-container');
    
    // Add keyboard accessibility
    this.container.setAttribute('tabindex', '-1');

    // Create spinner container
    this.spinner = document.createElement('div');
    this.spinner.className = `sa-spinner sa-${this.options.animationStyle}`;
    this.container.appendChild(this.spinner);

    // Create spinner elements based on style
    this.createSpinnerElements();

    // Create icon container if enabled
    if (this.options.showIcon) {
      this.phaseIcon = document.createElement('div');
      this.phaseIcon.className = 'sa-icon';
      this.container.appendChild(this.phaseIcon);
    }

    // Create phase text element
    this.phaseText = document.createElement('div');
    this.phaseText.className = 'sa-phase-text';
    this.phaseText.setAttribute('aria-live', 'polite');
    this.phaseText.setAttribute('aria-atomic', 'true');
    this.container.appendChild(this.phaseText);

    // Create progress bar if enabled
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
    this.container.setAttribute('aria-label', 'Search animation');

    // Hidden text for screen readers (must NOT have aria-hidden)
    this.srText = document.createElement('span');
    this.srText.className = 'sr-only';
    this.container.appendChild(this.srText);
  }

  /**
   * Create spinner elements based on animation style
   */
  createSpinnerElements() {
    switch (this.options.animationStyle) {
      case 'pulsing-ring':
        const ring = document.createElement('div');
        ring.className = 'sa-pulsing-ring';
        this.spinner.appendChild(ring);
        break;

      case 'bouncing-bars':
        for (let i = 0; i < 3; i++) {
          const bar = document.createElement('div');
          bar.className = 'sa-bar';
          this.spinner.appendChild(bar);
        }
        break;

      case 'chasing-dots':
      default:
        for (let i = 0; i < 3; i++) {
          const dot = document.createElement('div');
          dot.className = 'sa-dot';
          this.spinner.appendChild(dot);
        }
        break;
    }
  }

  /**
   * Start the animation sequence
   * @param {Array} phases - Optional phase override
   */
  start(phases) {
    if (phases) {
      this.options.phases = phases;
    }

    // Reset state
    this.currentPhaseIndex = 0;
    this.isAnimating = true;
    this.isError = false;
    this.startTime = Date.now();

    // Update UI
    this.container.classList.add('sa-animating');
    this.container.classList.remove('sa-error', 'sa-complete');
    this.container.setAttribute('aria-busy', 'true');

    // Show progress bar if enabled
    if (this.progressBar) {
      this.progressBar.classList.add('visible');
    }

    // Start with first phase
    this.updatePhase();

    // Emit phase change event
    this.emit('phaseChange', this.getPhaseEventData());

    // Only start client-side phase progression if SSE is NOT connected
    // If SSE will connect later, it will call stopClientSideProgression()
    if (!this.sseConnected) {
      this.startClientSideProgression();
    }
  }

  /**
   * Start client-side phase progression as fallback
   * Phases will advance automatically based on estimated durations
   */
  startClientSideProgression() {
    if (!this.options.phases || !this.isAnimating || this.sseConnected) return;

    // Clear any existing timer
    if (this.phaseTimer) {
      clearTimeout(this.phaseTimer);
    }

    const phase = this.options.phases[this.currentPhaseIndex];
    if (!phase) return;

    // Get estimated duration or use default
    const duration = phase.estimatedDurationMs || 1000;

    // Advance to next phase after duration
    this.phaseTimer = setTimeout(() => {
      // Only advance if still animating, not at the last phase, and SSE not connected
      if (this.isAnimating && !this.sseConnected && this.currentPhaseIndex < this.options.phases.length - 1) {
        this.currentPhaseIndex++;
        this.updatePhase();
        this.emit('phaseChange', this.getPhaseEventData());
        this.startClientSideProgression(); // Continue progression
      }
    }, duration);
  }

  /**
   * Stop client-side phase progression
   */
  stopClientSideProgression() {
    if (this.phaseTimer) {
      clearTimeout(this.phaseTimer);
      this.phaseTimer = null;
    }
  }

  /**
   * Connect to SSE endpoint for real-time phase updates
   * Falls back to client-side estimation if SSE not available
   */
  connectSSE() {
    // SSE is optional - if it fails, we use client-side estimation
    this.sseConnected = false;
    
    try {
      // Close existing connection if any
      if (this.eventSource) {
        this.eventSource.close();
      }

      const url = this.options.sseEndpoint;
      this.eventSource = new EventSource(url);

      this.eventSource.onopen = () => {
        this.sseConnected = true;
        this.stopClientSideProgression();
      };

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.phase) this.nextPhase(data.phase);
          if (data.progress !== undefined) this.setProgress(data.progress);
          if (data.error) {
            this.error(data.error_message || 'Search failed');
          } else if (data.complete) {
            this.complete();
          }
        } catch (e) {
          // ignore parse errors
        }
      };

      this.eventSource.onerror = (error) => {
        this.sseConnected = false;
        // Don't log - connection errors are expected (e.g., when search completes)
      };

    } catch (error) {
      // Don't log - SSE not supported is handled by client-side estimation
      this.sseConnected = false;
    }
  }

  /**
   * Advance to the specified phase
   * @param {string} phaseId - The phase ID to transition to
   */
  nextPhase(phaseId) {
    // Validate that phaseId is a string from our known phases
    if (typeof phaseId !== 'string') {
      console.error('SearchAnimation: Invalid phaseId type, must be string');
      return;
    }
    
    const phaseIndex = this.options.phases.findIndex(p => p.id === phaseId);
    
    if (phaseIndex >= 0) {
      this.currentPhaseIndex = phaseIndex;
      this.updatePhase();
      this.emit('phaseChange', this.getPhaseEventData());
    } else {
      console.error(`SearchAnimation: Unknown phase "${phaseId}"`);
    }
  }

  /**
   * Update current phase display
   */
  updatePhase() {
    const phase = this.options.phases[this.currentPhaseIndex];
    
    // Update screen reader text
    if (this.srText && phase) {
      this.srText.textContent = `Search phase: ${phase.label}`;
    }

    // Ensure phase exists and has a label
    if (!phase || !phase.label) {
      console.error('SearchAnimation: Invalid phase, cannot update display');
      return;
    }

    // Check for fun message opportunity (10% chance during fetch phase)
    if (this.currentPhaseIndex === 1 && this.options.phases.length > 3) {
      const randomIndex = Math.floor(Math.random() * 10);
      if (randomIndex === 0) {
        const funMessage = SearchAnimation.FUN_MESSAGES[
          Math.floor(Math.random() * SearchAnimation.FUN_MESSAGES.length)
        ];
        this.phaseText.textContent = funMessage;
        this.phaseText.classList.add('sa-fun-message');
        // Update screen reader text for fun message
        if (this.srText) {
          this.srText.textContent = `Search phase: ${funMessage}`;
        }
      } else {
        this.phaseText.textContent = phase.label;
        this.phaseText.classList.remove('sa-fun-message');
      }
    } else {
      this.phaseText.textContent = phase.label;
      this.phaseText.classList.remove('sa-fun-message');
    }

    // Update progress
    if (this.options.showProgressBar) {
      const progress = ((this.currentPhaseIndex + 1) / this.options.phases.length) * 100;
      this.progressFill.style.width = `${Math.min(progress, 100)}%`;
      this.emit('progress', { percentage: progress });
    }

    // Update phase class for styling
    // Remove all phase classes first
    this.container.classList.remove(
      'sa-phase-initiating', 'sa-phase-fetching', 'sa-phase-filtering',
      'sa-phase-ranking', 'sa-phase-loading', 'sa-phase-complete'
    );
    
    // Add current phase class
    if (phase && phase.id) {
      this.container.classList.add(`sa-phase-${phase.id}`);
    }

    // Update icon if enabled and icon exists
    if (this.options.showIcon && this.phaseIcon && phase && phase.icon) {
      const iconUrl = `${this.options.iconPath}/${phase.icon}.svg`;
      this.phaseIcon.innerHTML = `<img src="${iconUrl}" alt="${phase.id}" class="sa-icon-image">`;
    }

    // Trigger micro-interaction animation
    if (this.spinner) {
      this.spinner.classList.add('sa-phase-change');
      setTimeout(() => {
        this.spinner.classList.remove('sa-phase-change');
      }, 300);
    }

    // Update colors if defined
    if (phase.color) {
      const colors = phase.color.split(',').map(c => c.trim());
      this.spinner.querySelectorAll('.sa-dot, .sa-bar, .sa-pulsing-ring').forEach((el, index) => {
        el.style.backgroundColor = colors[index % colors.length];
        if (el.classList.contains('sa-pulsing-ring')) {
          el.style.borderTopColor = colors[0];
        }
      });
    }
  }

  /**
   * Manually set the progress percentage
   * @param {number} percentage - Progress value (0-100)
   */
  setProgress(percentage) {
    if (this.options.showProgressBar) {
      this.progressFill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
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

    // Stop client-side progression
    this.stopClientSideProgression();

    // Close SSE connection
    this.closeSSE();

    this.emit('complete');
  }

  /**
   * Close SSE connection
   */
  closeSSE() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.sseConnected = false;
  }

  /**
   * Put animation in error state
   * @param {string} message - Error message to display
   */
  error(message) {
    this.isAnimating = false;
    this.isError = true;
    this.container.classList.remove('sa-animating', 'sa-complete');
    this.container.classList.add('sa-error');
    this.container.setAttribute('aria-busy', 'false');

    this.phaseText.textContent = message;
    this.phaseText.classList.remove('sa-fun-message');

    // Stop client-side progression
    this.stopClientSideProgression();

    // Close SSE connection
    this.closeSSE();

    this.emit('error', { message });
  }

  /**
   * Reset animation to initial state
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
    this.phaseText.classList.remove('sa-fun-message');

    // Stop client-side progression
    this.stopClientSideProgression();

    // Close SSE connection
    this.closeSSE();
  }

  /**
   * Register event listener
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   */
  on(event, callback) {
    if (!this.eventListeners[event]) {
      this.eventListeners[event] = [];
    }
    this.eventListeners[event].push(callback);
  }

  /**
   * Emit event to all listeners
   * @param {string} event - Event name
   * @param {Object} data - Event data
   */
  emit(event, data) {
    if (this.eventListeners[event]) {
      this.eventListeners[event].forEach(callback => callback(data));
    }
  }

  /**
   * Get current phase event data
   * @returns {Object} Phase data for events
   */
  getPhaseEventData() {
    const phase = this.options.phases[this.currentPhaseIndex];
    return {
      phaseId: phase.id,
      message: this.phaseText.textContent,
      index: this.currentPhaseIndex,
      timestamp: Date.now()
    };
  }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SearchAnimation;
}
