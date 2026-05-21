"""
Tradera scraper - for tradera.com second-hand listings.
"""

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
        Scrape Tradera listings from search results.
        Uses __NEXT_DATA__ JSON if available (server-side rendered data),
        falls back to HTML parsing for client-side rendered pages.
        """
        url = f"https://www.tradera.com/en/search?q={urllib.parse.quote_plus(query)}"
        listings = []

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=config.SCRAPER_TIMEOUT) as s:
            try:
                resp = await s.get(url)
                
                # First, try to extract data from __NEXT_DATA__ JSON
                # This is more reliable as Tradera uses Next.js with server-side data
                next_data = self._extract_next_data(resp.text)
                if next_data:
                    listings = self._parse_next_data(next_data, max_results)
                else:
                    # Fallback: parse HTML (for older pages or if JSON extraction fails)
                    self.log_debug("[yellow]Tradera: No __NEXT_DATA__ found, falling back to HTML parsing[/yellow]")
                    soup = BeautifulSoup(resp.text, "html.parser")
                    listings = await self._parse_html(soup, max_results)

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
                
                # Extract price - try multiple fields
                # buyNowPrice is the fixed price, price is the current bid/starting price
                price = float(item.get("buyNowPrice", item.get("price", 0)) or 0)
                
                # Determine currency - Tradera uses SEK as default
                # Check for explicit currency field, otherwise default to SEK
                # (Tradera is a Swedish site, prices are typically in SEK)
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
                
                listings.append(Listing(
                    title=title,
                    price=price,
                    currency=currency,
                    url=item_url,
                    description=description,
                    platform=self.platform,
                    date_posted=date_posted,
                ))
                
        except Exception as e:
            self.log_debug(f"[red]Tradera: Error parsing __NEXT_DATA__: {e}[/red]")
        
        return listings
    
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

            listings.append(Listing(
                title=title,
                price=price,
                currency=currency,
                url=full_url,
                description=description,
                platform=self.platform,
                date_posted=date_posted,
            ))
        
        return listings
