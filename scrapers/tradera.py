"""
Tradera scraper - for tradera.com second-hand listings.
"""

import re
import urllib.parse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

from models import Listing
from scrapers.base import BaseScraper
import config

console = Console()


class TraderaScraper(BaseScraper):
    """Scraper for Tradera.com second-hand listings."""
    
    platform = "Tradera"
    
    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
        """
        Scrape Tradera listings from search results.
        """
        url = f"https://www.tradera.com/en/search?q={urllib.parse.quote_plus(query)}"
        listings = []

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=config.SCRAPER_TIMEOUT) as s:
            try:
                resp = await s.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Try multiple selector strategies
                cards = [tag for tag in soup.find_all("div", id=re.compile(r"^item-card-\d+"))]
                
                self.log_debug(f"[blue]Tradera: Found {len(cards)} cards with primary selector[/blue]")
                
                # Alternative: look for any div with item-related content
                if not cards:
                    cards = soup.find_all("div", class_=re.compile(r"item|product|listing"))
                    self.log_debug(f"[blue]Tradera: Found {len(cards)} cards with alternative selector[/blue]")
                
                # Filter to ensure we have actual item containers
                # Each card should contain at least one link to an item
                filtered_cards = []
                for card in cards:
                    # Check if card contains a link to an item page
                    link = card.select_one('a[href*="/item/"]')
                    if link and link.get('href'):
                        filtered_cards.append(card)
                
                self.log_debug(f"[blue]Tradera: {len(filtered_cards)} valid cards after link filtering[/blue]")
                
                if not filtered_cards:
                    filtered_cards = cards  # Fall back to all
                
                cards = filtered_cards[:max_results]

                seen_urls = set()
                for card in cards:
                    # Title: first link pointing to /en/item/
                    link_el = card.select_one('a[href^="/en/item/"]')
                    if not link_el:
                        # Try broader search for any link in the card
                        link_el = card.select_one('a[href*="/item/"]')
                    
                    href    = link_el.get("href", "") if link_el else ""
                    
                    # Skip if no valid href
                    if not href:
                        continue
                    
                    # Skip if this URL was already processed
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    # Title: first try to get text from link
                    title = link_el.get_text(strip=True) if link_el else None
                    
                    # If title is empty, extract from URL slug
                    if not title:
                        # URL format: /en/item/260103/730697864/ny-pixel-9a-med-grapheneos
                        # Extract the last slug part
                        slug_match = re.search(r'/item/[^/]+/[^/]+/([^/]+)/?$', href)
                        if slug_match:
                            slug = slug_match.group(1)
                            # Convert slug to title (replace hyphens with spaces, capitalize)
                            title = slug.replace('-', ' ').title()
                        else:
                            self.log_debug(f"[yellow]Tradera: Could not extract slug from {href}[/yellow]")
                            continue

                    self.log_debug(f"[dim]Tradera: title='{title}', href={href}[/dim]")

                    # Price: Extract from search results (may be auction bid or Buy Now price)
                    price_el = None
                    price = 0.0
                    currency = "DKK"
                    
                    # Look for any span containing a price (with currency)
                    for span in card.find_all("span"):
                        text = span.get_text(strip=True)
                        
                        # Check if this span has a price format
                        if re.search(r'[\d\.\s,]+\s*(dkk|sek|eur)', text, re.IGNORECASE):
                            p = self.parse_price(text)
                            if 0 < p < 1000000:  # Sanity check
                                # Determine currency
                                if "DKK" in text.upper():
                                    currency = "DKK"
                                elif "SEK" in text.upper():
                                    currency = "SEK"
                                else:
                                    currency = "DKK"  # Default
                                
                                price = p
                                price_el = span
                                self.log_debug(f"[dim]Tradera price: {price} {currency} from '{text[:40]}'[/dim]")
                                break  # Use the first valid price found

                    full_url = (
                        f"https://www.tradera.com{href}"
                        if href.startswith("/")
                        else href
                    )
                    
                    # Description: try to extract from the card
                    description = ""
                    desc_el = card.select_one('[class*="description"], [class*="excerpt"], [class*="summary"]')
                    if desc_el:
                        description = desc_el.get_text(strip=True)[:300]

                    # Date posted: try to extract from the card
                    date_posted = ""
                    date_el = card.select_one('[class*="date"], [class*="time"], [class*="posted"], [class*="published"], [class*="ends"]')
                    if date_el:
                        date_posted = date_el.get_text(strip=True)
                    else:
                        # Try to find time tag
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

            except Exception as e:
                console.print(f"[red]Tradera error: {e}[/red]")

        console.print(f"[green]Tradera:[/green] {len(listings)} listings found")
        return listings
