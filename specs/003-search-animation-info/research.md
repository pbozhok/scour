# Research: Informative Search Animation

**Feature**: Informative Search Animation with "fun to look at" requirement
**Date**: 2026-05-28
**Status**: Complete

## Decisions

### Decision 1: Animation Style - Playful yet Professional

**Decision**: Use a combination of SVG-based progress indicators with smooth CSS transitions and micro-interactions. The animation will feature a "chasing dots" or "pulsing ring" pattern that morphs between states, with status text that fades in/out.

**Rationale**: 
- SVG provides crisp, scalable graphics that work on all screen sizes
- CSS transitions ensure 60 FPS performance on all devices
- Micro-interactions (subtle bounces, fades) add the "fun" element without being distracting
- The chasing/pulsing pattern is universally recognized as "loading" while being visually engaging
- Text updates provide the informational aspect required by the spec

**Alternatives considered**:
- GIF animations: Rejected due to larger file sizes and less control over timing
- Canvas animations: Rejected due to complexity and potential performance issues
- Pure CSS spinners: Rejected as not "fun" enough for the requirement
- Lottie/JSON animations: Rejected to avoid adding new dependencies

### Decision 2: Progress State Communication - Client-Side with Estimates

**Decision**: Implement client-side progress estimation with server-provided phase milestones. The frontend will show estimated progress based on typical phase durations, with the backend optionally providing phase change notifications via WebSocket or polling.

**Rationale**:
- Reduces backend complexity (no need for server-sent events initially)
- Provides immediate visual feedback
- Can be enhanced later with real-time updates
- Works within existing FastAPI architecture

**Alternatives considered**:
- Server-Sent Events (SSE): More accurate but adds backend complexity
- WebSockets: Real-time but overkill for progress updates
- Polling API endpoint: Simple but adds latency

### Decision 3: Fun Elements Implementation

**Decision**: Incorporate the following "fun" elements:
1. **Color transitions**: Smooth color shifts between phases (e.g., blue → purple → green)
2. **Micro-interactions**: Subtle bounce animation when transitioning between states
3. **Custom icons**: SVG icons that represent each phase (search icon, filter icon, checkmark)
4. **Progress bar**: Animated progress bar with gradient fill
5. **Easter egg**: On long searches, occasionally show a fun message (e.g., "Hunting for deals...")

**Rationale**: These elements add visual interest and personality while remaining professional and not distracting from the core functionality. They satisfy the "make it fun to look at" requirement without compromising usability.

**Alternatives considered**:
- Animated mascots: Too brand-specific and potentially distracting
- Particle effects: Performance concerns on mobile devices
- Sound effects: Accessibility issues and user preferences vary

### Decision 4: Accessibility Implementation

**Decision**: 
- All animations respect `prefers-reduced-motion` media query
- Status text is always visible and readable
- ARIA live regions announce status changes to screen readers
- Minimum contrast ratio of 4.5:1 for all text
- Animations can be paused/frozen without losing information

**Rationale**: WCAG compliance is mandatory. These techniques ensure the animation is accessible to all users while maintaining the fun visual elements for those who can perceive them.

**Alternatives considered**: None - these are standard accessibility requirements.

### Decision 5: Integration Approach

**Decision**: Create a standalone `SearchAnimation` JavaScript class that can be instantiated with a container element. The class will handle all animation logic, state transitions, and status text updates. CSS will be scoped to avoid conflicts.

**Rationale**: 
- Modular design aligns with constitution principles
- Reusable across different pages if needed
- Easy to test in isolation
- Can be replaced or enhanced without affecting other code

**Alternatives considered**:
- Inline script in HTML template: Less maintainable
- Framework-specific component: Not applicable (no frontend framework)
- Global CSS animations: Potential for style conflicts

### Decision 6: Search Phase Definitions

**Decision**: Define the following standard phases for the second-hand search process:
1. **Initiating**: "Starting your search..."
2. **Fetching**: "Fetching listings from sources..."
3. **Filtering**: "Applying your filters..."
4. **Ranking**: "Ranking results by relevance..."
5. **Loading**: "Loading results..."
6. **Complete**: "Done!"

**Rationale**: These phases map to the actual backend pipeline (scrapers → filters → processors → rankers). They provide meaningful information to users about what the system is actually doing.

**Alternatives considered**: Generic "Loading..." only - rejected as it doesn't provide useful information.

## Best Practices Applied

1. **Animation Performance**: All animations use `transform` and `opacity` properties (GPU-accelerated) for 60 FPS performance
2. **CSS Scoping**: Animation styles use BEM-like naming convention (`.sa-` prefix) to prevent conflicts
3. **Progressive Enhancement**: Animation works without JavaScript (fallback to simple spinner), enhanced with JS enabled
4. **Responsive Design**: Animation adapts to container size, works on mobile and desktop
5. **Error States**: Clear error messaging with retry options

## Technical References

- FastAPI Static Files: https://fastapi.tiangolo.com/tutorial/static-files/
- CSS Animations: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations
- ARIA Live Regions: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/ARIA_Live_Regions
- prefers-reduced-motion: https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion
