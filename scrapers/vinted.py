"""
Vinted scraper - for vinted.dk second-hand listings.
"""

import asyncio

from rich.console import Console
from models import Listing
from scrapers.base import BaseScraper
import config
from core.logging import get_logger
from core.module import ModuleType

console = Console()
logger = get_logger(__name__, module_name="scrapers.vinted")


class VintedScraper(BaseScraper):
    """Scraper for Vinted.dk second-hand listings."""
    
    name = "vinted-scraper"
    module_type = ModuleType.SCRAPER
    version = "1.0.0"
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

            per_page = min(max_results, 96)  # Vinted's practical per-page limit

            def _fetch(page: int, attempt: int = 0):
                try:
                    scraper = VintedScraperLib("https://www.vinted.dk")
                    return scraper.search({"search_text": query, "per_page": per_page, "page": page})
                except Exception as e:
                    error_str = str(e)
                    if "406" in error_str and attempt < max_retries:
                        wait_time = (2 ** attempt) * 5
                        console.print(f"[yellow]Vinted 406 error. Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...[/yellow]")
                        return None
                    else:
                        self.log_debug(f"[yellow]Vinted scraper error: {e}[/yellow]")
                        return []

            seen_ids: set = set()
            page = 1

            while len(listings) < max_results:
                items = None
                for attempt in range(max_retries):
                    items = await asyncio.get_event_loop().run_in_executor(None, _fetch, page, attempt)
                    if items is not None:
                        break
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 5
                        await asyncio.sleep(wait_time)

                if not items:
                    if page == 1:
                        self.log_debug("[yellow]Vinted: No items returned from scraper[/yellow]")
                    break

                new_items = [it for it in items if getattr(it, 'id', None) not in seen_ids]
                if not new_items:
                    break

                self.log_debug(f"[blue]Vinted page {page}: {len(new_items)} new items[/blue]")
                page += 1

                for item in new_items:
                    if len(listings) >= max_results:
                        break
                    item_id = getattr(item, 'id', None)
                    if item_id:
                        seen_ids.add(item_id)

                    # VintedItem exposes attributes directly — no .get() needed
                    try:
                        title       = item.title or "Unknown"
                        price       = float(item.price) if item.price else 0.0
                        currency    = item.currency or "DKK"
                        url         = item.url or ""
                        description = item.description or ""

                        # Extract images
                        images = []

                        if hasattr(item, 'photo') and item.photo:
                            photo = item.photo
                            if isinstance(photo, dict):
                                photo_url = photo.get('url', '')
                                if photo_url:
                                    images.append(photo_url)
                            elif isinstance(photo, str):
                                images.append(photo)

                        if hasattr(item, 'photos') and item.photos:
                            for photo in item.photos:
                                if hasattr(photo, 'url') and photo.url:
                                    images.append(photo.url)
                                elif isinstance(photo, dict) and 'url' in photo:
                                    images.append(photo['url'])

                        json_data = getattr(item, 'json_data', {})
                        if json_data and 'photos' in json_data:
                            for photo in json_data['photos']:
                                if isinstance(photo, dict):
                                    if 'url' in photo:
                                        images.append(photo['url'])
                                    elif 'full_size_url' in photo:
                                        images.append(photo['full_size_url'])

                        if images:
                            images = list(dict.fromkeys(images))[:3]

                        date_posted = ""
                        if json_data:
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
                            images=images,
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
