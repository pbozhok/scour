"""
Tradera scraper - for tradera.com second-hand listings.
"""

import asyncio
import json
import re
import urllib.parse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

from models import Listing
from scrapers.base import BaseScraper
import config
from core.logging import get_logger
from core.module import ModuleType

console = Console()
logger = get_logger(__name__, module_name="scrapers.tradera")


class TraderaScraper(BaseScraper):
    """Scraper for Tradera.com second-hand listings."""
    
    name = "tradera-scraper"
    module_type = ModuleType.SCRAPER
    version = "1.0.0"
    platform = "Tradera"
    
    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
        """
        Scrape Tradera listings from search results, paginating until max_results reached.
        Uses __NEXT_DATA__ JSON if available, falls back to HTML parsing.
        After collecting all listings, fetches detail pages for any with price=0.
        """
        base_url = f"https://www.tradera.com/en/search?q={urllib.parse.quote_plus(query)}"
        listings = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=config.SCRAPER_TIMEOUT) as s:
            try:
                for page in range(1, 11):
                    if len(listings) >= max_results:
                        break

                    url = f"{base_url}&page={page}" if page > 1 else base_url
                    try:
                        resp = await s.get(url)
                    except Exception:
                        break

                    next_data = self._extract_next_data(resp.text)
                    if next_data:
                        page_listings = self._parse_next_data(next_data, max_results - len(listings))
                    else:
                        self.log_debug(f"[yellow]Tradera page {page}: No __NEXT_DATA__, falling back to HTML[/yellow]")
                        soup = BeautifulSoup(resp.text, "html.parser")
                        page_listings = await self._parse_html(soup, max_results - len(listings))

                    new_listings = [l for l in page_listings if l.url not in seen_urls]
                    if not new_listings:
                        break

                    self.log_debug(f"[blue]Tradera page {page}: {len(new_listings)} new listings[/blue]")
                    for l in new_listings:
                        seen_urls.add(l.url)
                    listings.extend(new_listings)

                # Fetch detail pages for any listings where price is still 0
                zero_price = [l for l in listings if l.price == 0]
                if zero_price:
                    self.log_debug(f"[yellow]Tradera: fetching detail pages for {len(zero_price)} zero-price items[/yellow]")
                    sem = asyncio.Semaphore(8)
                    await asyncio.gather(
                        *[self._fetch_detail_price(s, listing, sem) for listing in zero_price],
                        return_exceptions=True,
                    )

            except Exception as e:
                console.print(f"[red]Tradera error: {e}[/red]")

        console.print(f"[green]Tradera:[/green] {len(listings)} listings found")
        return listings
    
    def _extract_next_data(self, html: str) -> dict | None:
        """Extract __NEXT_DATA__ JSON from HTML."""
        try:
            # Look for the __NEXT_DATA__ script tag
            match = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>',
                html,
                re.DOTALL
            )
            if match:
                data_str = match.group(1).strip()
                return json.loads(data_str)
        except (json.JSONDecodeError, AttributeError) as e:
            self.log_debug(f"[yellow]Tradera: Failed to parse __NEXT_DATA__: {e}[/yellow]")
        return None
    
    def _parse_next_data(self, next_data: dict, max_results: int) -> list[Listing]:
        """Parse item listings from __NEXT_DATA__ JSON."""
        listings = []
        seen_urls = set()
        
        try:
            # Navigate to items in the nested structure
            # Path: props.pageProps.initialState.discover.items
            items = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("initialState", {})
                .get("discover", {})
                .get("items", [])
            )
            
            if not items:
                self.log_debug("[yellow]Tradera: No items found in __NEXT_DATA__[/yellow]")
                return listings
            
            self.log_debug(f"[blue]Tradera: Found {len(items)} items in __NEXT_DATA__[/blue]")
            
            for item in items[:max_results]:
                # Extract basic info
                item_id = item.get("itemId", "")
                title = item.get("shortDescription", "") or item.get("title", "")
                
                if not title:
                    continue
                
                # Handle URL
                item_url = item.get("itemUrl", "")
                if not item_url:
                    # Construct URL from item ID if needed
                    category_id = item.get("categoryId", "")
                    slug = title.lower().replace(" ", "-")
                    item_url = f"https://www.tradera.com/en/item/{category_id}/{item_id}/{slug}"
                
                # Skip duplicates
                if item_url in seen_urls:
                    continue
                seen_urls.add(item_url)
                
                # Extract price — use `or` chaining so None values fall through to the next field
                price_val = (
                    item.get("buyNowPrice") or
                    item.get("price") or
                    item.get("currentHighBidAmount") or
                    item.get("minimumBidAmount") or
                    item.get("reservationPrice") or
                    0
                )
                price = float(price_val or 0)

                currency_str = item.get("priceCurrency", "SEK").upper()
                currency = currency_str if currency_str in ["DKK", "SEK", "EUR"] else "SEK"
                
                self.log_debug(f"[dim]Tradera: item_id={item_id}, title='{title}', price={price} {currency}, url={item_url}[/dim]")
                
                # Extract date
                start_date = item.get("startDate", "")
                if start_date:
                    try:
                        # Parse ISO date format
                        date_posted = datetime.fromisoformat(start_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                    except (ValueError, AttributeError):
                        date_posted = start_date[:10]  # Just use the date part
                else:
                    date_posted = ""
                
                # Extract description
                description = item.get("description", "") or ""
                if description:
                    description = description[:300]
                
                # Extract images from __NEXT_DATA__
                images = []
                
                # Try new format: imageUrlTemplate (current Tradera structure)
                image_template = item.get("imageUrlTemplate")
                if image_template:
                    # imageUrlTemplate might be a string or a dict
                    if isinstance(image_template, str):
                        # Try to construct URL from template
                        # Tradera templates use various placeholders: {format}, {0}, etc.
                        # Common patterns:
                        # - "https://img.tradera.net/{format}/000/no_image" (no-image placeholder)
                        # - "//images.tradera.com/{0}/..." (with index placeholder)
                        base_url = image_template
                        
                        # Replace common placeholders
                        for placeholder in ["{format}", "{0}", "{index}", "{size}"]:
                            if placeholder in base_url:
                                # Use a reasonable default for the placeholder
                                if placeholder == "{format}":
                                    base_url = base_url.replace(placeholder, "medium")
                                else:
                                    base_url = base_url.replace(placeholder, "0")
                        
                        # Ensure URL has protocol
                        if base_url.startswith("//"):
                            base_url = f"https:{base_url}"
                        elif base_url.startswith("/"):
                            base_url = f"https://www.tradera.com{base_url}"
                        
                        if base_url:
                            images.append(base_url)
                    elif isinstance(image_template, dict):
                        url = image_template.get("url", "") or image_template.get("href", "")
                        if url:
                            if url.startswith("//"):
                                url = f"https:{url}"
                            elif url.startswith("/"):
                                url = f"https://www.tradera.com{url}"
                            images.append(url)
                
                # Try old format: photos array (legacy)
                if not images:
                    photos = item.get("photos") or []
                    if photos:
                        for photo in photos:
                            if isinstance(photo, dict):
                                url = photo.get("url", "") or photo.get("imageUrl", "")
                                if url:
                                    if url.startswith("//"):
                                        url = f"https:{url}"
                                    elif url.startswith("/"):
                                        url = f"https://www.tradera.com{url}"
                                    images.append(url)
                            elif isinstance(photo, str):
                                images.append(photo)
                
                if images:
                    images = list(dict.fromkeys(images))[:3]
                
                listings.append(Listing(
                    title=title,
                    price=price,
                    currency=currency,
                    url=item_url,
                    description=description,
                    platform=self.platform,
                    date_posted=date_posted,
                    images=images,
                ))
                
        except Exception as e:
            self.log_debug(f"[red]Tradera: Error parsing __NEXT_DATA__: {e}[/red]")
        
        return listings
    
    async def _fetch_detail_price(self, s: httpx.AsyncClient, listing: Listing, sem: asyncio.Semaphore) -> None:
        """Fetch item detail page to recover price when search results return 0."""
        async with sem:
            try:
                resp = await s.get(listing.url, timeout=15)
                # Try __NEXT_DATA__ on detail page first (more reliable)
                next_data = self._extract_next_data(resp.text)
                if next_data:
                    # Item detail pages keep data at props.pageProps.item (or similar paths)
                    item_data = (
                        next_data.get("props", {}).get("pageProps", {}).get("item")
                        or next_data.get("props", {}).get("pageProps", {}).get("initialState", {}).get("item", {})
                        or {}
                    )
                    price_val = (
                        item_data.get("buyNowPrice") or
                        item_data.get("price") or
                        item_data.get("currentHighBidAmount") or
                        item_data.get("minimumBidAmount") or
                        0
                    )
                    if price_val:
                        listing.price = float(price_val)
                        currency_str = item_data.get("priceCurrency", "SEK").upper()
                        listing.currency = currency_str if currency_str in ["DKK", "SEK", "EUR"] else "SEK"
                        return

                # Fallback: scan HTML for a price-like element
                soup = BeautifulSoup(resp.text, "html.parser")
                for el in soup.find_all(["span", "div", "p", "strong", "b"]):
                    text = el.get_text(strip=True)
                    if len(text) > 50:
                        continue
                    if re.search(r'\d[\d\s.]*\s*(DKK|SEK|kr)', text, re.IGNORECASE):
                        price = self.parse_price(text)
                        if price > 0:
                            listing.price = price
                            if "DKK" in text.upper():
                                listing.currency = "DKK"
                            elif "SEK" in text.upper() or "kr" in text.lower():
                                listing.currency = "SEK"
                            return
            except Exception:
                pass

    async def _parse_html(self, soup: BeautifulSoup, max_results: int) -> list[Listing]:
        """Fallback: Parse HTML for item cards (legacy method)."""
        listings = []

        # Try multiple selector strategies
        cards = [tag for tag in soup.find_all("div", id=re.compile(r"^item-card-\d+"))]
        
        self.log_debug(f"[blue]Tradera: Found {len(cards)} cards with primary selector[/blue]")
        
        # Alternative: look for any div with item-related content
        if not cards:
            cards = soup.find_all("div", class_=re.compile(r"item|product|listing"))
            self.log_debug(f"[blue]Tradera: Found {len(cards)} cards with alternative selector[/blue]")
        
        # Filter to ensure we have actual item containers
        filtered_cards = []
        for card in cards:
            link = card.select_one('a[href*="/item/"]')
            if link and link.get('href'):
                filtered_cards.append(card)
        
        self.log_debug(f"[blue]Tradera: {len(filtered_cards)} valid cards after link filtering[/blue]")
        
        if not filtered_cards:
            filtered_cards = cards
        
        cards = filtered_cards[:max_results]

        seen_urls = set()
        for card in cards:
            link_el = card.select_one('a[href^="/en/item/"]')
            if not link_el:
                link_el = card.select_one('a[href*="/item/"]')
            
            href = link_el.get("href", "") if link_el else ""
            
            if not href:
                continue
            
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            title = link_el.get_text(strip=True) if link_el else None
            
            if not title:
                slug_match = re.search(r'/item/[^/]+/[^/]+/([^/]+)/?$', href)
                if slug_match:
                    slug = slug_match.group(1)
                    title = slug.replace('-', ' ').title()
                else:
                    self.log_debug(f"[yellow]Tradera: Could not extract slug from {href}[/yellow]")
                    continue

            self.log_debug(f"[dim]Tradera: title='{title}', href={href}[/dim]")

            price = 0.0
            currency = "SEK"  # Tradera default currency
            
            for span in card.find_all("span"):
                text = span.get_text(strip=True)
                
                if re.search(r'[\d\.\s,]+\s*(dkk|sek|eur)', text, re.IGNORECASE):
                    p = self.parse_price(text)
                    if 0 < p < 1000000:
                        if "DKK" in text.upper():
                            currency = "DKK"
                        elif "SEK" in text.upper():
                            currency = "SEK"
                        elif "EUR" in text.upper():
                            currency = "EUR"
                        
                        price = p
                        self.log_debug(f"[dim]Tradera price: {price} {currency} from '{text[:40]}'[/dim]")
                        break

            full_url = (
                f"https://www.tradera.com{href}"
                if href.startswith("/")
                else href
            )
            
            description = ""
            desc_el = card.select_one('[class*="description"], [class*="excerpt"], [class*="summary"]')
            if desc_el:
                description = desc_el.get_text(strip=True)[:300]

            date_posted = ""
            date_el = card.select_one('[class*="date"], [class*="time"], [class*="posted"], [class*="published"], [class*="ends"]')
            if date_el:
                date_posted = date_el.get_text(strip=True)
            else:
                time_el = card.find("time")
                if time_el:
                    date_posted = time_el.get("datetime", time_el.get_text(strip=True))
            
            # Extract images
            images = []
            for img_el in card.find_all('img', src=True):
                src = img_el.get('src', '').strip()
                if src and not src.startswith('data:'):
                    if src.startswith('//'):
                        src = f"https:{src}"
                    elif src.startswith('/'):
                        src = f"https://www.tradera.com{src}"
                    images.append(src)
            if images:
                images = list(dict.fromkeys(images))[:3]

            listings.append(Listing(
                title=title,
                price=price,
                currency=currency,
                url=full_url,
                description=description,
                platform=self.platform,
                date_posted=date_posted,
                images=images,
            ))
        
        return listings
