"""
Scrapers module - platform-specific scraper implementations.

This module provides the scraping functionality for the second-hand research agent.
All scrapers inherit from BaseScraper which implements the Module interface.

Available scrapers:
- DBAScraper: For DBA.dk (Danish marketplace)
- VintedScraper: For Vinted.dk (European fashion marketplace)
- TraderaScraper: For Tradera.com (Swedish marketplace)

Usage:
    from scrapers import DBAScraper, VintedScraper, TraderaScraper
    
    scraper = DBAScraper(debug=True)
    listings = await scraper.scrape("iPhone 15", max_results=20)
"""

from .base import BaseScraper
from .dba import DBAScraper
from .vinted import VintedScraper
from .tradera import TraderaScraper

# Auto-register scrapers with the global registry
from core.registry import registry

# Create instances and register
try:
    registry.register(DBAScraper(debug=False))
    registry.register(VintedScraper(debug=False))
    registry.register(TraderaScraper(debug=False))
except ValueError as e:
    # Already registered - this is fine
    pass

__all__ = ["BaseScraper", "DBAScraper", "VintedScraper", "TraderaScraper", "registry"]
