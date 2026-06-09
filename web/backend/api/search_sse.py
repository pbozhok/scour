"""
Server-Sent Events (SSE) endpoint for real-time search phase updates.

This module provides SSE endpoints that stream phase transition events
during the search process, allowing the frontend to display real-time
progress information to users.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search", "sse"])


# Global state to track active searches and their phase
# In production, use a proper store (Redis, database) for distributed environments
active_searches = {}


class SearchProgressTracker:
    """
    Tracks the progress of a search through its various phases.
    Emits events when phases change.
    """
    
    # Phase definitions matching the frontend expectations
    PHASES = [
        {"id": "initiating", "label": "Starting your search...", "order": 1},
        {"id": "fetching", "label": "Fetching listings from sources...", "order": 2},
        {"id": "filtering", "label": "Applying your filters...", "order": 3},
        {"id": "ranking", "label": "Ranking results by relevance...", "order": 4},
        {"id": "loading", "label": "Loading results...", "order": 5},
        {"id": "complete", "label": "Done!", "order": 6},
    ]
    
    def __init__(self, search_id: str):
        self.search_id = search_id
        self.current_phase_index = 0
        self.is_complete = False
        self.is_error = False
        self.error_message = ""
        self.progress = int(1 / len(self.PHASES) * 100)
    
    @property
    def current_phase(self):
        """Get current phase info."""
        if self.current_phase_index < len(self.PHASES):
            return self.PHASES[self.current_phase_index]
        return self.PHASES[-1]
    
    def next_phase(self):
        """Advance to the next phase."""
        if self.current_phase_index < len(self.PHASES) - 1:
            self.current_phase_index += 1
            self.progress = int((self.current_phase_index / len(self.PHASES)) * 100)
            return self.current_phase
        return None
    
    def set_error(self, message: str):
        """Set error state."""
        self.is_error = True
        self.is_complete = True
        self.error_message = message
    
    def complete(self):
        """Mark search as complete."""
        self.is_complete = True
        self.current_phase_index = len(self.PHASES) - 1
        self.progress = 100
    
    def get_state(self) -> dict:
        """Get current state as a dictionary."""
        state = {
            "search_id": self.search_id,
            "phase": self.current_phase["id"],
            "label": self.current_phase["label"],
            "progress": self.progress,
            "complete": self.is_complete,
            "error": self.is_error,
        }
        if self.is_error:
            state["error_message"] = self.error_message
        return state


async def get_search_tracker(search_id: str) -> SearchProgressTracker:
    """Get or create a search tracker."""
    if search_id not in active_searches:
        active_searches[search_id] = SearchProgressTracker(search_id)
    return active_searches[search_id]


@router.get("/phases")
async def stream_search_phases(
    request: Request,
    search_id: str = "default"
) -> EventSourceResponse:
    """
    SSE endpoint that streams search phase updates.
    
    The frontend connects to this endpoint to receive real-time updates
    about which phase the search is currently in.
    
    Example usage:
    ```javascript
    const eventSource = new EventSource('/search/phases?search_id=abc123');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // data = {phase: 'fetching', label: '...', progress: 40, ...}
    };
    ```
    """
    tracker = await get_search_tracker(search_id)
    
    async def event_generator():
        """Generate SSE events for phase updates."""
        try:
            last_phase = None
            last_progress = -1
            while not tracker.is_complete:
                # Send current state
                state = tracker.get_state()
                current_phase = state.get('phase')
                current_progress = state.get('progress', 0)
                
                # Send if phase changed, progress updated, or there's an error
                if (last_phase != current_phase or 
                    last_progress != current_progress or 
                    tracker.is_error):
                    yield {"data": json.dumps(state)}
                    last_phase = current_phase
                    last_progress = current_progress
                
                # Short sleep for responsive updates
                await asyncio.sleep(0.1)
            
            # Send final complete state
            state = tracker.get_state()
            yield {"data": json.dumps(state)}
            
        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE client disconnected for search: {search_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for {search_id}: {e}")
            yield {"data": json.dumps({"error": True, "error_message": str(e)})}
    
    return EventSourceResponse(event_generator())


@router.get("/phases/poll")
async def poll_search_phase(
    search_id: str = "default"
) -> dict:
    """
    Polling endpoint to get current search phase (fallback if SSE not supported).
    
    Returns the current state of the search as JSON.
    """
    tracker = await get_search_tracker(search_id)
    return tracker.get_state()


# Cleanup function to remove completed searches
async def cleanup_searches():
    """Remove completed searches from the active_searches dict."""
    completed = [sid for sid, tracker in active_searches.items() if tracker.is_complete]
    for sid in completed:
        del active_searches[sid]
    if completed:
        logger.info(f"Cleaned up {len(completed)} completed searches")
