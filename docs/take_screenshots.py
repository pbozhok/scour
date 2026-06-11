"""Retake README screenshots using demo mode (no LLM pipeline)."""
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    # Landing screenshot
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    page.screenshot(path="docs/screenshot_landing.png")
    print("landing done")

    # Settings screenshot
    page.click("#config-btn")
    page.wait_for_selector("#config-modal-body input", timeout=5000)
    page.screenshot(path="docs/screenshot_settings.png")
    print("settings done")
    page.click("#config-modal-close")
    page.wait_for_timeout(200)

    # Results screenshot — demo mode gives instant results
    page.goto(f"{BASE}?demo")
    page.wait_for_load_state("networkidle")
    page.fill("#search-query", "Pixel 9a")
    page.click(".search-button")
    page.wait_for_selector(".cards-grid", timeout=5000)
    page.wait_for_timeout(600)  # let stagger animations settle
    # The loading animation waits for an SSE event that never fires in demo mode — hide it
    page.evaluate("document.getElementById('search-animation').style.display = 'none'")
    page.screenshot(path="docs/screenshot_results.png")
    print("results done")

    browser.close()
