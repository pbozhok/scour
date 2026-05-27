"""
DBA scraper - for dba.dk second-hand listings.
"""

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


def _parse_dba_date(date_str: str) -> str:
    """
    Parse DBA date string and convert to ISO format YYYY-MM-DD.
    
    DBA date formats:
    - "Sidst redigeret: 28.3.2026 kl. 08:23"
    - "28.3.2026 kl. 08:23"
    - "28.3.2026"
    - "2026-03-28" (ISO from meta tags)
    
    Returns: ISO date string "YYYY-MM-DD" or empty string if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return ""
    
    date_str = date_str.strip()
    
    # Already in ISO format
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        return date_str
    
    # Try to extract DD.MM.YYYY pattern
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
    if match:
        day, month, year = match.groups()
        try:
            # Parse and reformat to ensure validity
            dt = datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return ""
    
    return ""

console = Console()
logger = get_logger(__name__, module_name="scrapers.dba")


class DBAScraper(BaseScraper):
    """Scraper for DBA.dk recommerce listings."""
    
    name = "dba-scraper"
    module_type = ModuleType.SCRAPER
    version = "1.0.0"
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
                    
                    # For very low prices, this might be a parsing error
                    # DBA uses DKK, so prices should typically be > 10
                    if price < 10 and price > 0:
                        self.log_debug(f"[yellow]DBA suspicious low price: {price} for {title[:50]}[/yellow]")
                    
                    if self.debug:
                        if price_el:
                            self.log_debug(f"[dim]DBA price: {price_text} -> {price}[/dim]")
                        else:
                            self.log_debug(f"[yellow]DBA no price found for {title}[/yellow]")

                    # Description: try to extract from the card or parent
                    description = ""
                    if card.parent:
                        desc_el = card.parent.select_one('[class*="description"], [class*="excerpt"], [class*="summary"]')
                        if desc_el:
                            description = desc_el.get_text(strip=True)[:300]

                    # Date posted: For DBA, always fetch from the detail page to get accurate posting date
                    date_posted = ""
                    full_url = (
                        f"https://www.dba.dk{href}"
                        if href.startswith("/")
                        else href
                    )
                    
                    # Always fetch the detail page for DBA to get the posting date and description
                    if full_url:
                        try:
                            detail_resp = await s.get(full_url, timeout=15)
                            resp_text = detail_resp.text
                            
                            # Parse detail page HTML
                            try:
                                detail_soup = BeautifulSoup(resp_text, features="html.parser")
                            except:
                                detail_soup = BeautifulSoup(detail_resp.content, features="html.parser")
                            
                            # Extract description from detail page if not already found
                            if not description:
                                desc_section = detail_soup.find('section', {'data-testid': 'description'})
                                if desc_section:
                                    # Try get_text with space separator
                                    description = desc_section.get_text(' ', strip=True)
                                    if not description or len(description) < 10:
                                        # Fallback: extract text directly from raw HTML
                                        # Find the description section in raw text
                                        desc_start = resp_text.find('data-testid="description"')
                                        if desc_start >= 0:
                                            # Find the closing > of the opening section tag
                                            tag_end = resp_text.find('>', desc_start)
                                            if tag_end >= 0:
                                                desc_end = resp_text.find('</section>', tag_end)
                                                if desc_end >= 0:
                                                    desc_html = resp_text[tag_end+1:desc_end]
                                                    # Remove HTML tags and comments
                                                    desc_clean = re.sub(r'<[^>]+>', ' ', desc_html)
                                                    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
                                                    description = desc_clean[:500]
                            
                            # Try to find date in meta tags first
                            
                            meta_date = detail_soup.find('meta', attrs={'property': 'article:published_time'})
                            if meta_date and meta_date.get('content'):
                                date_posted = _parse_dba_date(meta_date.get('content'))
                            
                            if not date_posted:
                                # Check for ISO date in other meta tags
                                for meta_tag in detail_soup.find_all('meta'):
                                    content = meta_tag.get('content', '')
                                    if content and re.match(r'\d{4}-\d{2}-\d{2}', content):
                                        date_posted = _parse_dba_date(content)
                                        break
                            
                            if not date_posted:
                                # Extract date directly from raw response text
                                # This is more reliable as BeautifulSoup.get_text() can miss content
                                # due to malformed HTML or web components
                                date_match = re.search(
                                    r'(?:Sidst redigeret|Oprettet|Dato|Postet)\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4}\s*(?:kl\.\s*)?\d{1,2}:\d{2})'
                                    r'|(\d{1,2}\.\d{1,2}\.\d{4}\s*(?:kl\.\s*)?\d{1,2}:\d{2})',
                                    resp_text,
                                    re.IGNORECASE
                                )
                                if date_match:
                                    date_posted = _parse_dba_date((date_match.group(1) or date_match.group(2)).strip())
                            
                            # Fallback: check all time elements in parsed soup
                            if not date_posted:
                                for time_el in detail_soup.find_all("time"):
                                    datetime_val = time_el.get("datetime")
                                    if datetime_val:
                                        date_posted = _parse_dba_date(datetime_val)
                                        break
                                    text = time_el.get_text(strip=True)
                                    if text and len(text) > 5:
                                        date_posted = _parse_dba_date(text)
                                        break
                            
                            # Last resort: find any date pattern in raw text
                            if not date_posted:
                                date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
                                date_match = re.search(date_pattern, resp_text)
                                if date_match:
                                    date_posted = _parse_dba_date(date_match.group(0))
                        except httpx.TimeoutException:
                            pass
                        except httpx.HTTPStatusError:
                            pass
                        except Exception:
                            pass

                    # Extract images
                    images = []
                    # Look for img tags in card and parent
                    for img_el in card.find_all('img', src=True):
                        src = img_el.get('src', '').strip()
                        if src and not src.startswith('data:'):
                            # Make absolute URL if relative
                            if src.startswith('/'):
                                src = f"https://www.dba.dk{src}"
                            images.append(src)
                    # If no images found in card, try parent
                    if not images and card.parent:
                        for img_el in card.parent.find_all('img', src=True):
                            src = img_el.get('src', '').strip()
                            if src and not src.startswith('data:'):
                                if src.startswith('/'):
                                    src = f"https://www.dba.dk{src}"
                                images.append(src)
                    # Deduplicate and limit to first 3
                    if images:
                        images = list(dict.fromkeys(images))[:3]

                    listings.append(Listing(
                        title=title,
                        price=price,
                        currency="DKK",
                        url=full_url,
                        description=description,
                        platform=self.platform,
                        date_posted=date_posted,
                        images=images,
                    ))

            except Exception as e:
                console.print(f"[red]DBA error: {e}[/red]")

        console.print(f"[green]DBA:[/green] {len(listings)} listings found")
        return listings
