"""
DBA scraper - for dba.dk second-hand listings.
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


class DBAScraper(BaseScraper):
    """Scraper for DBA.dk recommerce listings."""
    
    platform = "DBA"
    
    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
        """
        Scrape DBA listings using the recommerce URL structure.
        Search page: https://www.dba.dk/recommerce/forsale/search?q=...
        """
        url = f"https://www.dba.dk/recommerce/forsale/search?q={urllib.parse.quote_plus(query)}"
        listings = []

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=config.SCRAPER_TIMEOUT) as s:
            try:
                resp = await s.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Try multiple selector strategies - look for listing cards/containers first
                # DBA listings are typically in div/article elements with specific classes
                cards = soup.select('a[href*="/recommerce/forsale/item/"]')
                
                # Filter to only those that are likely actual listing cards
                # by checking if they're inside a listing container (div, article, li, etc.)
                filtered_cards = []
                for card in cards:
                    parent = card.parent
                    # Check if parent looks like a listing container
                    if parent and parent.name in ('div', 'article', 'li', 'section'):
                        # Additional check: parent should have some content (not just a nav link)
                        parent_text = parent.get_text(strip=True)
                        if len(parent_text) > 10:  # Has meaningful content
                            filtered_cards.append(card)
                
                self.log_debug(f"[blue]DBA: Found {len(cards)} cards with primary selector, {len(filtered_cards)} after filtering[/blue]")
                
                # If no cards found, try alternative selectors
                if not filtered_cards:
                    filtered_cards = cards  # Fall back to all cards
                    self.log_debug(f"[blue]DBA: Using all cards as fallback[/blue]")
                
                cards = filtered_cards[:max_results]

                seen_urls = set()
                for i, card in enumerate(cards):
                    href = card.get("href", "")
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # Title: get the card's text content
                    title = card.get_text(strip=True)
                    
                    self.log_debug(f"[dim]DBA card {i} text: '{title}'[/dim]")
                    
                    # If link text is empty, look at the parent container
                    if not title:
                        parent = card.parent
                        if parent:
                            # Try to find title in nearby elements
                            title_el = parent.select_one('h2, h3, h4, [class*="title"], [class*="name"], [data-testid*="title"]')
                            if title_el:
                                title = title_el.get_text(strip=True)
                                self.log_debug(f"[dim]DBA found in parent: '{title}'[/dim]")
                            else:
                                # Try to get all text from parent (more aggressive)
                                title = parent.get_text(strip=True)[:200]
                                self.log_debug(f"[dim]DBA from parent text: '{title[:80]}'[/dim]")
                    
                    # If still no title, extract from URL
                    if not title or len(title) < 2:
                        match = re.search(r'/item/(\d+)', href)
                        if match:
                            title = f"DBA Item {match.group(1)}"
                        else:
                            continue
                    
                    # Clean title if it contains price info (e.g., "MAC MINI M4 - 12999 kr")
                    title_parts = re.split(r'\d+\s*(kr|dkk|eur|€|\$)|(kr|dkk|eur|€|\$)\s*\d+|\d+[.,\s]\d+\s*(kr|dkk|eur|€|\$)', title, flags=re.IGNORECASE)
                    title = title_parts[0].strip() if title_parts else title
                    
                    # Price: first look for common price patterns in the card
                    # Try elements with price-related classes first
                    price_el = None
                    price_text = ""
                    
                    # Search in card, then parent, then broader
                    for search_area in [card, card.parent if card.parent else None, None]:
                        if not search_area:
                            continue
                        
                        # Try specific price class patterns
                        price_el = search_area.select_one('[class*="price"], [class*="pris"], [class*="amount"], [class*="beløb"]')
                        if price_el:
                            price_text = price_el.get_text(strip=True)
                            self.log_debug(f"[blue]DBA price class match: {price_text}[/blue]")
                            break
                        
                        # Try data-price attribute
                        price_el = search_area.select_one('[data-price], [data-price], [data-amount]')
                        if price_el:
                            price_text = price_el.get('data-price', '') or price_el.get('data-amount', '') or price_el.get_text(strip=True)
                            self.log_debug(f"[blue]DBA price data attr: {price_text}[/blue]")
                            break
                        
                        # Try finding elements with price-like numeric patterns
                        for tag in search_area.find_all(['span', 'div', 'p', 'strong', 'b', 'price']):
                            text = tag.get_text(strip=True)
                            # Look for patterns like "12.999", "12999", "12 999" with optional kr/dkk
                            if re.search(r'\d{1,3}[\.\s,]\d{3,}(\s*(kr|dkk))?', text, re.IGNORECASE):
                                price_el = tag
                                price_text = text
                                self.log_debug(f"[blue]DBA price pattern match: {price_text}[/blue]")
                                break
                        
                        if price_el:
                            break
                    
                    # Last resort: use the original method
                    if not price_el:
                        price_el = card.find(
                            lambda tag: tag.name in ("span", "div", "p")
                            and "kr" in tag.get_text().lower()
                            and len(tag.get_text(strip=True)) < 30
                        )
                        if price_el:
                            price_text = price_el.get_text(strip=True)
                        elif card.parent:
                            price_el = card.parent.find(
                                lambda tag: tag.name in ("span", "div", "p")
                                and "kr" in tag.get_text().lower()
                                and len(tag.get_text(strip=True)) < 30
                            )
                            if price_el:
                                price_text = price_el.get_text(strip=True)
                    
                    if not price_text:
                        price_text = "0"
                    
                    price = self.parse_price(price_text)
                    
                    # For very low prices from DKK listings, this might be a parsing error
                    # 12999 DKK should be ~1700 EUR, not 2 EUR
                    if price < 10 and price > 0 and listing.currency == "DKK":
                        self.log_debug(f"[yellow]DBA suspicious low price: {price} DKK for {title[:50]}[/yellow]")
                    
                    if self.debug:
                        if price_el:
                            self.log_debug(f"[dim]DBA price: {price_text} -> {price}[/dim]")
                        else:
                            self.log_debug(f"[yellow]DBA no price found for {title}[/yellow]")

                    full_url = (
                        f"https://www.dba.dk{href}"
                        if href.startswith("/")
                        else href
                    )
                    
                    # Description: try to extract from the card or parent
                    description = ""
                    if card.parent:
                        desc_el = card.parent.select_one('[class*="description"], [class*="excerpt"], [class*="summary"]')
                        if desc_el:
                            description = desc_el.get_text(strip=True)[:300]

                    # Date posted: try to extract from the card's article container
                    date_posted = ""
                    # Find the article ancestor which contains the date
                    article = card.find_parent('article')
                    if article:
                        article_text = article.get_text()
                        # Look for relative date patterns like "Nyt i dag", "2 dage", "8 t.", etc.
                        # t. = timer (hours), d. = dage (days)
                        date_match = re.search(r'(Nyt i (dag|g\u00e5r)|(\d+)\s*(dage?|d\.|uge(r)?|m\u00e5ned(er)?|t\.)|Oprettet\s*:?\s*(\S+))', article_text, re.I)
                        if date_match:
                            date_posted = date_match.group(0).strip()
                            # Clean up the date text
                            date_posted = re.sub(r'\s+', ' ', date_posted)
                        else:
                            # Try looking for date elements
                            date_el = article.select_one('[class*="date"], [class*="time"], [class*="posted"], [class*="published"], [class*="oprettet"]')
                            if date_el:
                                date_posted = date_el.get_text(strip=True)
                            else:
                                # Try time tag
                                time_el = article.find("time")
                                if time_el:
                                    date_posted = time_el.get("datetime", time_el.get_text(strip=True))
                    elif card.parent:
                        # Fallback to parent
                        date_el = card.parent.select_one('[class*="date"], [class*="time"], [class*="posted"], [class*="published"], [class*="oprettet"]')
                        if date_el:
                            date_posted = date_el.get_text(strip=True)
                        else:
                            time_el = card.parent.find("time")
                            if time_el:
                                date_posted = time_el.get("datetime", time_el.get_text(strip=True))

                    listings.append(Listing(
                        title=title,
                        price=price,
                        currency="DKK",
                        url=full_url,
                        description=description,
                        platform=self.platform,
                        date_posted=date_posted,
                    ))

            except Exception as e:
                console.print(f"[red]DBA error: {e}[/red]")

        console.print(f"[green]DBA:[/green] {len(listings)} listings found")
        return listings
