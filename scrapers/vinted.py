"""
Vinted scraper - for vinted.dk second-hand listings.
"""

import asyncio

from rich.console import Console
from models import Listing
from scrapers.base import BaseScraper
import config

console = Console()


class VintedScraper(BaseScraper):
    """Scraper for Vinted.dk second-hand listings."""
    
    platform = "Vinted"
    
    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
        """
        Scrape Vinted listings using the vinted-scraper package.
        Uses the synchronous scraper in a thread to avoid blocking the event loop.
        """
        listings = []
        max_retries = 3

        try:
            from vinted_scraper import VintedScraper as VintedScraperLib

            # Run the synchronous scraper in a thread so it doesn't block the event loop
            def _fetch(attempt: int = 0):
                try:
                    scraper = VintedScraperLib("https://www.vinted.dk")
                    return scraper.search({"search_text": query, "per_page": max_results})
                except Exception as e:
                    error_str = str(e)
                    if "406" in error_str and attempt < max_retries:
                        # 406 error: retry with exponential backoff
                        wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                        console.print(f"[yellow]Vinted 406 error. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...[/yellow]")
                        return None  # Signal retry needed
                    else:
                        self.log_debug(f"[yellow]Vinted scraper error: {e}[/yellow]")
                        return []

            # Retry loop
            items = None
            for attempt in range(max_retries):
                items = await asyncio.get_event_loop().run_in_executor(None, _fetch, attempt)
                if items is not None:
                    break
                # Wait before retrying
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5
                    await asyncio.sleep(wait_time)

            if items is None:
                items = []

            if not items:
                self.log_debug(f"[yellow]Vinted: No items returned from scraper[/yellow]")

            for item in items[:max_results]:
                # VintedItem exposes attributes directly — no .get() needed
                try:
                    title       = item.title or "Unknown"
                    price       = float(item.price) if item.price else 0.0
                    currency    = item.currency or "DKK"
                    url         = item.url or ""
                    description = item.description or ""
                    
                    # Try to extract date from json_data
                    date_posted = ""
                    json_data = getattr(item, 'json_data', {})
                    if json_data:
                        # Check for timestamp in photos[0]['high_resolution']['timestamp']
                        if 'photos' in json_data and json_data['photos']:
                            first_photo = json_data['photos'][0]
                            if 'high_resolution' in first_photo and isinstance(first_photo['high_resolution'], dict):
                                timestamp = first_photo['high_resolution'].get('timestamp')
                                if timestamp:
                                    import datetime
                                    date_posted = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                            elif 'timestamp' in first_photo:
                                import datetime
                                date_posted = datetime.datetime.fromtimestamp(first_photo['timestamp']).strftime('%Y-%m-%d')
                    
                    listings.append(Listing(
                        title=title,
                        price=price,
                        currency=currency,
                        url=url,
                        description=description,
                        platform=self.platform,
                        date_posted=date_posted,
                    ))
                except AttributeError as e:
                    self.log_debug(f"[yellow]Vinted item parse error (skipping): {e}[/yellow]")
                    continue

        except ImportError:
            console.print("[yellow]Vinted: install with 'pip install vinted-scraper'[/yellow]")
        except Exception as e:
            self.log_debug(f"[yellow]Vinted error (continuing anyway): {e}[/yellow]")

        console.print(f"[green]Vinted:[/green] {len(listings)} listings found")
        return listings
