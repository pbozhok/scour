"""
User configuration manager.

Loads user_config.json (gitignored) and applies overrides to environment
variables so they take effect for subsequent pipeline runs.
"""

import json
import os
from pathlib import Path

_CONFIG_FILE = Path(__file__).parent / "user_config.json"

DEFAULTS = {
    "api_keys": {
        "mistral": "",
        "gemini": "",
        "serpapi": "",
    },
    "search": {
        "default_max_results": 40,
        "default_currency": "EUR",
        "default_max_keywords": 3,
    },
    "pipeline": {
        "scraper_timeout": 20,
        "max_retries": 5,
        "batch_size": 60,
        "delay_between_batches": 0.5,
    },
    "reviews": {
        "max_review_results": 3,
        "review_delay": 4.0,
    },
}

_user_config: dict = {}


def load() -> None:
    global _user_config
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                _user_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            _user_config = {}
    else:
        _user_config = {}
    _apply_env()


def save(data: dict) -> None:
    global _user_config
    _user_config = data
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    _apply_env()


def get() -> dict:
    return _user_config


def get_value(section: str, key: str, default=None):
    return _user_config.get(section, {}).get(key, default)


def effective(section: str, key: str):
    """Return user override if set, otherwise the default value."""
    user_val = _user_config.get(section, {}).get(key)
    if user_val is not None and user_val != "":
        return user_val
    return DEFAULTS.get(section, {}).get(key)


def _apply_env() -> None:
    keys = _user_config.get("api_keys", {})
    if keys.get("mistral"):
        os.environ["MISTRAL_API_KEY"] = keys["mistral"]
    if keys.get("gemini"):
        os.environ["GOOGLE_API_KEY"] = keys["gemini"]
        os.environ["GEMINI_API_KEY"] = keys["gemini"]
    if keys.get("serpapi"):
        os.environ["SERPAPI_KEY"] = keys["serpapi"]


# Apply on import
load()
