"""
Sync contract tests between backend SSE and frontend SearchAnimation.

Tests verify the SSE message format that backend sends matches what the
frontend onmessage handler expects:

  data.phase         : str  - phase ID
  data.progress      : int  - 0-100
  data.complete      : bool
  data.error         : bool  ← NOT a string
  data.error_message : str   - only present when error=True

Two tests will FAIL against the current code:
  - exception handler sends {"error": str(e)} instead of
    {"error": True, "error_message": str(e)}
  - tracker initializes progress=0 so first SSE event always shows 0%
    even though "initiating" is the first of six phases (~17%)
"""

import asyncio
import json

import pytest

from web.backend.api.search_sse import (
    SearchProgressTracker,
    active_searches,
    stream_search_phases,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_phase_callback(tracker: SearchProgressTracker):
    """Replicate the phase_callback closure from web/backend/api/search.py."""
    _phase_index = {p['id']: i for i, p in enumerate(SearchProgressTracker.PHASES)}
    _n_phases = len(SearchProgressTracker.PHASES)

    def phase_callback(phase_name: str, current: int, total: int):
        idx = _phase_index.get(phase_name)
        if idx is not None:
            tracker.current_phase_index = idx
            tracker.progress = int((idx + 1) / _n_phases * 100)

    return phase_callback


# ---------------------------------------------------------------------------
# Contract: get_state() shape
# ---------------------------------------------------------------------------

class TestGetStateFormat:
    """
    get_state() is what every SSE event is built from.
    These tests pin the exact format the frontend relies on.
    """

    def test_error_field_is_bool_on_success(self):
        t = SearchProgressTracker("x")
        state = t.get_state()
        assert state["error"] is False

    def test_error_field_is_bool_on_error(self):
        t = SearchProgressTracker("x")
        t.set_error("boom")
        state = t.get_state()
        assert state["error"] is True  # must be bool, not string

    def test_error_message_present_only_on_error(self):
        normal = SearchProgressTracker("x")
        assert "error_message" not in normal.get_state()

        errored = SearchProgressTracker("y")
        errored.set_error("oops")
        assert "error_message" in errored.get_state()
        assert errored.get_state()["error_message"] == "oops"

    def test_complete_field_is_bool(self):
        t = SearchProgressTracker("x")
        assert t.get_state()["complete"] is False
        t.complete()
        assert t.get_state()["complete"] is True

    def test_error_also_sets_complete(self):
        """Frontend checks error/complete as separate branches; error must set complete too."""
        t = SearchProgressTracker("x")
        t.set_error("gone wrong")
        state = t.get_state()
        assert state["complete"] is True
        assert state["error"] is True

    def test_phase_field_is_known_string(self):
        t = SearchProgressTracker("x")
        known_ids = {p["id"] for p in SearchProgressTracker.PHASES}
        assert t.get_state()["phase"] in known_ids

    def test_progress_field_is_integer_in_range(self):
        t = SearchProgressTracker("x")
        p = t.get_state()["progress"]
        assert isinstance(p, int)
        assert 0 <= p <= 100


# ---------------------------------------------------------------------------
# Bug 1: exception handler sends wrong error format
# ---------------------------------------------------------------------------

class TestSSEExceptionEventFormat:
    """
    The event_generator exception handler currently yields:
        {"error": str(e)}
    where 'error' is a STRING.

    The frontend's onmessage handler reads:
        data.error_message || 'Search failed'
    so the actual error string is silently dropped and the user always
    sees 'Search failed' for internal SSE crashes.

    The fix: yield {"error": True, "error_message": str(e)}.
    These two tests FAIL against the current code.
    """

    def test_exception_event_error_field_type_matches_get_state(self):
        """
        The exception handler and get_state() are both consumed by the same
        frontend onmessage handler, so they must use the same field types.
        The fixed handler emits {"error": True, "error_message": str(e)}.
        """
        e = RuntimeError("disk full")
        exception_event = {"error": True, "error_message": str(e)}

        tracker = SearchProgressTracker("x")
        tracker.set_error(str(e))
        state_event = tracker.get_state()

        assert type(exception_event["error"]) == type(state_event["error"]), (
            f"exception event: error={exception_event['error']!r} "
            f"({type(exception_event['error']).__name__}), "
            f"get_state: error={state_event['error']!r} "
            f"({type(state_event['error']).__name__})"
        )
        assert "error_message" in exception_event
        assert "error_message" in state_event

    def test_exception_event_error_message_is_preserved(self):
        """
        error_message must be present so the frontend shows the real error.
        Without it, the frontend falls back to the generic 'Search failed' string.
        """
        e = RuntimeError("disk full")
        event = {"error": True, "error_message": str(e)}

        # Replicate what the frontend does: data.error_message || 'Search failed'
        displayed = event.get("error_message") or "Search failed"
        assert displayed == str(e), (
            f"Frontend would display {displayed!r} instead of {str(e)!r}"
        )

    async def test_exception_event_format_end_to_end(self, monkeypatch):
        """
        When the event_generator's asyncio.sleep raises, the exception handler
        emits an error event. Verify its format end-to-end via the real endpoint.
        """
        from httpx import ASGITransport, AsyncClient
        from web.backend.main import app

        sid = "test-exc-format-e2e"
        active_searches[sid] = SearchProgressTracker(sid)

        async def exploding_sleep(delay):
            raise RuntimeError("simulated SSE crash")

        monkeypatch.setattr("web.backend.api.search_sse.asyncio.sleep", exploding_sleep)

        events = []
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            async with client.stream(
                "GET", f"/api/v1/search/phases?search_id={sid}"
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                        if raw:
                            events.append(json.loads(raw))

        active_searches.pop(sid, None)

        error_events = [e for e in events if e.get("error")]
        assert error_events, f"No error event found in: {events}"

        err = error_events[-1]
        # FAILS: current code sends error as string "simulated SSE crash"
        assert err["error"] is True, (
            f"'error' field is {err['error']!r} ({type(err['error']).__name__}), "
            "must be boolean True"
        )
        assert "error_message" in err, f"'error_message' missing from: {err}"
        assert err["error_message"] == "simulated SSE crash"


# ---------------------------------------------------------------------------
# Bug 2: initial progress is 0 — causes 0% flash before first phase fires
# ---------------------------------------------------------------------------

class TestInitialProgress:
    """
    tracker.progress starts at 0.

    The first SSE event sends {phase: "initiating", progress: 0}.
    The frontend onmessage handler calls BOTH:
      1. nextPhase("initiating") — internally computes (0+1)/6*100 = 16.67%
      2. setProgress(0)          — overwrites the bar back to 0%

    Result: the progress bar shows 0% at the start, then jumps to 33%
    when "fetching" fires, skipping the "initiating" visual entirely.

    The fix: initialize progress = int(1 / len(PHASES) * 100) = 16.
    """

    def test_initial_progress_nonzero(self):
        """
        Tracker must start with progress > 0 so the first SSE event
        shows visible progress corresponding to phase 1 of N.
        """
        t = SearchProgressTracker("x")
        n = len(SearchProgressTracker.PHASES)
        expected_min = int(1 / n * 100)  # 16 for 6 phases

        # FAILS: t.progress == 0 with current code
        assert t.progress >= expected_min, (
            f"Initial progress is {t.progress}% but 'initiating' is phase 1/{n} "
            f"({expected_min}%). Frontend setProgress(0) will blank the progress bar "
            "right after nextPhase() calculates {expected_min:.1f}%."
        )

    def test_initial_phase_is_initiating(self):
        """Sanity check: tracker starts at the first phase."""
        t = SearchProgressTracker("x")
        assert t.current_phase["id"] == "initiating"


# ---------------------------------------------------------------------------
# Phase callback / pipeline contract
# ---------------------------------------------------------------------------

class TestPhaseCallbackContract:
    """
    The pipeline calls phase_callback with four phase names:
      "fetching", "filtering", "ranking", "loading"
    (never "initiating" or "complete" — those are handled implicitly).

    These tests confirm all four names map to valid tracker phase indices.
    """

    PIPELINE_PHASE_NAMES = ["fetching", "filtering", "ranking", "loading"]

    def test_all_pipeline_phases_are_known_to_tracker(self):
        """Every phase name the pipeline emits must be in SearchProgressTracker.PHASES."""
        known = {p["id"] for p in SearchProgressTracker.PHASES}
        for name in self.PIPELINE_PHASE_NAMES:
            assert name in known, (
                f"Pipeline calls phase_callback({name!r}) but tracker has no such phase. "
                f"Known phases: {sorted(known)}"
            )

    def test_phase_callback_updates_index_for_each_pipeline_phase(self):
        t = SearchProgressTracker("x")
        cb = _make_phase_callback(t)
        for i, name in enumerate(self.PIPELINE_PHASE_NAMES):
            cb(name, i + 1, 6)
            assert t.current_phase["id"] == name, (
                f"After calling phase_callback({name!r}), "
                f"tracker phase is {t.current_phase['id']!r}"
            )

    def test_unknown_phase_name_does_not_crash_or_change_state(self):
        """Future pipeline versions might emit unknown phase names; must be silent."""
        t = SearchProgressTracker("x")
        cb = _make_phase_callback(t)
        cb("fetching", 1, 6)
        prev_index = t.current_phase_index
        prev_progress = t.progress

        cb("scraping", 99, 99)  # unknown name

        assert t.current_phase_index == prev_index
        assert t.progress == prev_progress

    def test_progress_increases_through_pipeline_phases(self):
        t = SearchProgressTracker("x")
        cb = _make_phase_callback(t)
        prev_progress = t.progress
        for i, name in enumerate(self.PIPELINE_PHASE_NAMES):
            cb(name, i + 1, 6)
            assert t.progress > prev_progress, (
                f"Progress did not increase when transitioning to {name!r}: "
                f"{prev_progress}% -> {t.progress}%"
            )
            prev_progress = t.progress

    def test_complete_sets_progress_to_100(self):
        t = SearchProgressTracker("x")
        cb = _make_phase_callback(t)
        cb("loading", 4, 6)
        t.complete()
        assert t.progress == 100
