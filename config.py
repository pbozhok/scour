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

# LLM Providers mapping for dependency injection
LLM_PROVIDERS = {
    "gemini": "llm.client.GeminiClient",
    "mistral": "llm.client.MistralClient",
}

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
BATCH_SIZE = 60  # For LLM filtering
DELAY_BETWEEN_BATCHES = 2.0 # seconds
DEFAULT_MAX_RESULTS = 40  # Default max results per scraper

# ── Query Processing Configuration ────────────────────────────────────────────

DEFAULT_MAX_KEYWORDS = int(os.getenv("DEFAULT_MAX_KEYWORDS", "3"))  # Default number of search keywords

# ── Review Configuration ──────────────────────────────────────────────────────

MAX_REVIEW_RESULTS = 3
REVIEW_DELAY = 4.0  # seconds between model searches


# ── Web Interface Configuration ─────────────────────────────────────────────

class WebConfig:
    """Configuration for the web interface."""
    
    # Server settings
    HOST = os.getenv("WEB_HOST", "0.0.0.0")
    PORT = int(os.getenv("WEB_PORT", "8000"))
    DEBUG = os.getenv("WEB_DEBUG", "false").lower() == "true"
    
    # CORS settings (for development, allow all)
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Static files and templates
    STATIC_DIR = "web/frontend/static"
    TEMPLATES_DIR = "web/frontend/templates"
    
    # API settings
    API_PREFIX = "/api/v1"
    MAX_CONCURRENT_SEARCHES = 10
    
    # Timeouts
    SEARCH_TIMEOUT_SECONDS = 30


# Web configuration instance
web_config = WebConfig()
