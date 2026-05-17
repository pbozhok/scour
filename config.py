"""
Configuration and constants for second-hand research agent.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── LLM Configuration ──────────────────────────────────────────────────────────

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta"
    f"/models/{GEMINI_MODEL}:generateContent"
)

# ── HTTP Configuration ────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Currency Configuration ────────────────────────────────────────────────────

# Exchange rates (approximate, relative to EUR)
EXCHANGE_RATES = {
    "EUR": 1.0,
    "DKK": 7.45,  # 1 EUR ≈ 7.45 DKK
    "SEK": 11.20,  # 1 EUR ≈ 11.20 SEK
}

# Default currency
DEFAULT_CURRENCY = "EUR"

# ── Scraper Configuration ─────────────────────────────────────────────────────

SCRAPER_TIMEOUT = 20  # seconds
MAX_RETRIES = 5
BATCH_SIZE = 20  # For LLM filtering
DELAY_BETWEEN_BATCHES = 10.0  # seconds
DEFAULT_MAX_RESULTS = 40  # Default max results per scraper

# ── Review Configuration ──────────────────────────────────────────────────────

MAX_REVIEW_RESULTS = 3
REVIEW_DELAY = 4.0  # seconds between model searches
