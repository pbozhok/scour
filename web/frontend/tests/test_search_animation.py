"""
Unit tests for search-animation.js — SearchAnimation class.

Uses Playwright (headless Chromium) to run the class in a real DOM so every
DOM API call (createElement, classList, setAttribute…) works without mocking.

Each test loads a minimal HTML page containing the script, then exercises the
class through page.evaluate() calls and asserts on DOM state.
"""

import pathlib
import pytest
from playwright.sync_api import Page, expect

JS_PATH = pathlib.Path(__file__).parents[2] / "frontend" / "static" / "js" / "search-animation.js"
JS_SRC = JS_PATH.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def anim_page(page: Page):
    """
    Load a minimal page with SearchAnimation available and a #container div.
    Returns the page ready to instantiate the class.
    """
    page.set_content("""
        <html><body>
          <div id="container"></div>
          <script>SCRIPT_PLACEHOLDER</script>
        </body></html>
    """.replace("SCRIPT_PLACEHOLDER", JS_SRC))
    return page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make(page: Page, opts: str = "{}") -> None:
    """Instantiate SearchAnimation on #container with given options."""
    page.evaluate(f"window.anim = new SearchAnimation('#container', {opts})")


# ---------------------------------------------------------------------------
# DOM initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_adds_sa_container_class(self, anim_page):
        make(anim_page)
        assert "sa-container" in anim_page.locator("#container").get_attribute("class")

    def test_creates_spinner_dots(self, anim_page):
        make(anim_page)
        assert anim_page.locator("#container .sa-dot").count() == 3

    def test_creates_phase_text(self, anim_page):
        make(anim_page)
        assert anim_page.locator("#container .sa-phase-text").count() == 1

    def test_phase_text_has_aria_live(self, anim_page):
        make(anim_page)
        assert anim_page.locator(".sa-phase-text").get_attribute("aria-live") == "polite"

    def test_creates_progress_bar_by_default(self, anim_page):
        make(anim_page)
        assert anim_page.locator("#container .sa-progress-bar").count() == 1

    def test_no_progress_bar_when_disabled(self, anim_page):
        make(anim_page, '{ showProgressBar: false }')
        assert anim_page.locator("#container .sa-progress-bar").count() == 0

    def test_role_is_status(self, anim_page):
        make(anim_page)
        assert anim_page.locator("#container").get_attribute("role") == "status"

    def test_sr_text_has_no_aria_hidden(self, anim_page):
        make(anim_page)
        attr = anim_page.locator("#container .sr-only").get_attribute("aria-hidden")
        # aria-hidden must be absent (None) — not "true"
        assert attr != "true"

    def test_pulsing_ring_style(self, anim_page):
        make(anim_page, '{ animationStyle: "pulsing-ring" }')
        # The spinner wrapper gets class sa-pulsing-ring AND the inner ring element
        # does too, so two elements carry this class — assert at least one exists.
        assert anim_page.locator("#container .sa-pulsing-ring").count() >= 1

    def test_bouncing_bars_style(self, anim_page):
        make(anim_page, '{ animationStyle: "bouncing-bars" }')
        assert anim_page.locator("#container .sa-bar").count() == 3

    def test_icon_container_created_when_enabled(self, anim_page):
        make(anim_page, '{ showIcon: true }')
        assert anim_page.locator("#container .sa-icon").count() == 1

    def test_no_icon_container_when_disabled(self, anim_page):
        make(anim_page, '{ showIcon: false }')
        assert anim_page.locator("#container .sa-icon").count() == 0

    def test_throws_on_missing_container(self, anim_page):
        err = anim_page.evaluate("""() => {
            try { new SearchAnimation('#nonexistent'); return null; }
            catch(e) { return e.message; }
        }""")
        assert err == "SearchAnimation: Container element not found"


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestStart:
    def test_adds_animating_class(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        assert "sa-animating" in anim_page.locator("#container").get_attribute("class")

    def test_removes_error_and_complete_classes(self, anim_page):
        make(anim_page)
        # Force both classes onto container first
        anim_page.evaluate("""() => {
            document.getElementById('container').classList.add('sa-error', 'sa-complete');
            anim.start();
        }""")
        classes = anim_page.locator("#container").get_attribute("class")
        assert "sa-error" not in classes
        assert "sa-complete" not in classes

    def test_sets_aria_busy_true(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        assert anim_page.locator("#container").get_attribute("aria-busy") == "true"

    def test_shows_first_phase_label(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        text = anim_page.locator(".sa-phase-text").inner_text()
        assert text == "Starting your search..."

    def test_progress_fill_at_first_phase(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        # 1/6 phases ≈ 16.6%
        assert width != "" and width != "0%"

    def test_custom_phases_override(self, anim_page):
        make(anim_page)
        anim_page.evaluate("""anim.start([
            { id: 'step1', label: 'Step one', color: '#000' },
            { id: 'step2', label: 'Step two', color: '#000' }
        ])""")
        assert anim_page.locator(".sa-phase-text").inner_text() == "Step one"

    def test_emits_phase_change_event(self, anim_page):
        make(anim_page)
        fired = anim_page.evaluate("""() => {
            let got = null;
            anim.on('phaseChange', data => got = data);
            anim.start();
            return got;
        }""")
        assert fired is not None
        assert fired["phaseId"] == "initiating"


# ---------------------------------------------------------------------------
# nextPhase()
# ---------------------------------------------------------------------------

class TestNextPhase:
    def test_updates_label(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.nextPhase('fetching')")
        assert "Fetching" in anim_page.locator(".sa-phase-text").inner_text()

    def test_updates_phase_class(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.nextPhase('filtering')")
        assert "sa-phase-filtering" in anim_page.locator("#container").get_attribute("class")

    def test_advances_progress_bar(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        w_before = anim_page.evaluate(
            "parseFloat(document.querySelector('.sa-progress-fill').style.width)"
        )
        anim_page.evaluate("anim.nextPhase('fetching')")
        w_after = anim_page.evaluate(
            "parseFloat(document.querySelector('.sa-progress-fill').style.width)"
        )
        assert w_after > w_before

    def test_unknown_phase_does_not_crash(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        # Should not throw
        anim_page.evaluate("anim.nextPhase('nonexistent')")
        assert anim_page.locator(".sa-phase-text").inner_text() == "Starting your search..."

    def test_non_string_phase_id_does_not_crash(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start()")
        anim_page.evaluate("anim.nextPhase(42)")
        # Should stay on initiating without crashing
        assert anim_page.locator(".sa-phase-text").inner_text() == "Starting your search..."

    def test_emits_phase_change_event(self, anim_page):
        make(anim_page)
        fired = anim_page.evaluate("""() => {
            let got = null;
            anim.on('phaseChange', data => got = data);
            anim.start();
            anim.nextPhase('ranking');
            return got;
        }""")
        assert fired["phaseId"] == "ranking"


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------

class TestComplete:
    def test_removes_animating_adds_complete(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete()")
        classes = anim_page.locator("#container").get_attribute("class")
        assert "sa-animating" not in classes
        assert "sa-complete" in classes

    def test_sets_aria_busy_false(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete()")
        assert anim_page.locator("#container").get_attribute("aria-busy") == "false"

    def test_shows_done_label(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete()")
        assert anim_page.locator(".sa-phase-text").inner_text() == "Done!"

    def test_progress_bar_at_100(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete()")
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        assert width == "100%"

    def test_emits_complete_event(self, anim_page):
        make(anim_page)
        fired = anim_page.evaluate("""() => {
            let got = false;
            anim.on('complete', () => got = true);
            anim.start();
            anim.complete();
            return got;
        }""")
        assert fired is True

    def test_does_not_add_error_class(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete()")
        assert "sa-error" not in anim_page.locator("#container").get_attribute("class")


# ---------------------------------------------------------------------------
# error()
# ---------------------------------------------------------------------------

class TestError:
    def test_adds_error_class(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.error('Something went wrong')")
        assert "sa-error" in anim_page.locator("#container").get_attribute("class")

    def test_removes_animating_class(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.error('oops')")
        assert "sa-animating" not in anim_page.locator("#container").get_attribute("class")

    def test_displays_message(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.error('Custom error message')")
        assert anim_page.locator(".sa-phase-text").inner_text() == "Custom error message"

    def test_sets_aria_busy_false(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.error('err')")
        assert anim_page.locator("#container").get_attribute("aria-busy") == "false"

    def test_emits_error_event_with_message(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            let got = null;
            anim.on('error', data => got = data);
            anim.start();
            anim.error('pipeline failed');
            return got;
        }""")
        assert result["message"] == "pipeline failed"

    def test_does_not_add_complete_class(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.error('oops')")
        assert "sa-complete" not in anim_page.locator("#container").get_attribute("class")


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestReset:
    def test_removes_state_classes(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete(); anim.reset()")
        classes = anim_page.locator("#container").get_attribute("class")
        assert "sa-animating" not in classes
        assert "sa-complete" not in classes
        assert "sa-error" not in classes

    def test_clears_phase_text(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.reset()")
        assert anim_page.locator(".sa-phase-text").inner_text() == ""

    def test_resets_progress_bar(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete(); anim.reset()")
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        assert width == "0%"

    def test_sets_aria_busy_false(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.reset()")
        assert anim_page.locator("#container").get_attribute("aria-busy") == "false"

    def test_can_restart_after_reset(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.start(); anim.complete(); anim.reset(); anim.start()")
        assert "sa-animating" in anim_page.locator("#container").get_attribute("class")


# ---------------------------------------------------------------------------
# setProgress()
# ---------------------------------------------------------------------------

class TestSetProgress:
    def test_sets_exact_percentage(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.setProgress(42)")
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        assert width == "42%"

    def test_clamps_above_100(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.setProgress(150)")
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        assert width == "100%"

    def test_clamps_below_0(self, anim_page):
        make(anim_page)
        anim_page.evaluate("anim.setProgress(-10)")
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        assert width == "0%"

    def test_no_op_when_progress_bar_disabled(self, anim_page):
        make(anim_page, '{ showProgressBar: false }')
        # Should not throw
        anim_page.evaluate("anim.setProgress(50)")


# ---------------------------------------------------------------------------
# SSE onmessage handler
# ---------------------------------------------------------------------------

class TestSSEOnMessage:
    """
    Test the onmessage handler by stubbing EventSource, calling connectSSE(),
    then dispatching synthetic messages and checking state.
    """

    SSE_STUB = """() => {
        // Stub EventSource so connectSSE() works without a server
        window._lastSSEHandlers = {};
        window.EventSource = class {
            constructor(url) { window._sse = this; }
            close() {}
        };
    }"""

    def _fire(self, page: Page, payload: dict) -> None:
        """Simulate an SSE message arriving."""
        import json
        page.evaluate(f"""() => {{
            if (window._sse && window._sse.onmessage)
                window._sse.onmessage({{ data: JSON.stringify({json.dumps(payload)}) }});
        }}""")

    def setup_sse(self, page: Page) -> None:
        make(page)
        page.evaluate(self.SSE_STUB)
        page.evaluate("anim.start(); anim.connectSSE()")

    def test_phase_message_updates_label(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {"phase": "filtering", "progress": 50, "complete": False, "error": False})
        assert "Applying" in anim_page.locator(".sa-phase-text").inner_text()

    def test_error_message_uses_error_message_field(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {
            "phase": "fetching", "progress": 30,
            "complete": True, "error": True,
            "error_message": "Scraper timeout"
        })
        assert anim_page.locator(".sa-phase-text").inner_text() == "Scraper timeout"

    def test_error_boolean_does_not_show_true_as_text(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {
            "phase": "fetching", "progress": 30,
            "complete": True, "error": True,
            "error_message": "Bad gateway"
        })
        assert anim_page.locator(".sa-phase-text").inner_text() != "true"

    def test_error_without_message_shows_fallback(self, anim_page):
        self.setup_sse(anim_page)
        # error=True but no error_message field
        self._fire(anim_page, {"phase": "fetching", "progress": 30, "complete": True, "error": True})
        assert anim_page.locator(".sa-phase-text").inner_text() == "Search failed"

    def test_error_message_sets_error_class_not_complete(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {
            "phase": "fetching", "progress": 30,
            "complete": True, "error": True,
            "error_message": "oops"
        })
        classes = anim_page.locator("#container").get_attribute("class")
        assert "sa-error" in classes
        assert "sa-complete" not in classes

    def test_complete_message_triggers_complete_state(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {"phase": "complete", "progress": 100, "complete": True, "error": False})
        assert "sa-complete" in anim_page.locator("#container").get_attribute("class")

    def test_complete_message_does_not_set_error_class(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {"phase": "complete", "progress": 100, "complete": True, "error": False})
        assert "sa-error" not in anim_page.locator("#container").get_attribute("class")

    def test_progress_message_updates_bar(self, anim_page):
        self.setup_sse(anim_page)
        self._fire(anim_page, {"phase": "fetching", "progress": 66, "complete": False, "error": False})
        width = anim_page.evaluate(
            "document.querySelector('.sa-progress-fill').style.width"
        )
        assert width == "66%"


# ---------------------------------------------------------------------------
# Client-side progression fallback
# ---------------------------------------------------------------------------

class TestClientSideProgression:
    def test_starts_when_sse_not_connected(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            anim.start();
            // Timer was created (phaseTimer is set)
            return anim.phaseTimer !== null;
        }""")
        assert result is True

    def test_stops_when_sse_connects(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            anim.start();
            const hadTimer = anim.phaseTimer !== null;
            // Simulate SSE connecting
            anim.sseConnected = true;
            anim.stopClientSideProgression();
            return { hadTimer, timerCleared: anim.phaseTimer === null };
        }""")
        assert result["hadTimer"] is True
        assert result["timerCleared"] is True

    def test_does_not_start_when_sse_already_connected(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            anim.sseConnected = true;
            anim.start();
            return anim.phaseTimer;
        }""")
        assert result is None


# ---------------------------------------------------------------------------
# Event system
# ---------------------------------------------------------------------------

class TestEvents:
    def test_on_registers_listener(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            let count = 0;
            anim.on('complete', () => count++);
            anim.start();
            anim.complete();
            return count;
        }""")
        assert result == 1

    def test_multiple_listeners_all_fire(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            let count = 0;
            anim.on('complete', () => count++);
            anim.on('complete', () => count++);
            anim.start();
            anim.complete();
            return count;
        }""")
        assert result == 2

    def test_progress_event_emitted_on_phase_update(self, anim_page):
        make(anim_page)
        result = anim_page.evaluate("""() => {
            let pct = null;
            anim.on('progress', data => pct = data.percentage);
            anim.start();
            anim.nextPhase('filtering');
            return pct;
        }""")
        assert result is not None
        assert result > 0
