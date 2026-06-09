"""
DBA scraper - for dba.dk second-hand listings.
"""

import asyncio
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

_DETAIL_CONCURRENCY = 8  # max simultaneous detail-page requests


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

    async def _fetch_detail(self, s: httpx.AsyncClient, listing: Listing, sem: asyncio.Semaphore) -> None:
        """Fetch a single DBA detail page and update listing in-place."""
        async with sem:
            try:
                detail_resp = await s.get(listing.url, timeout=15)
                resp_text = detail_resp.text

                try:
                    detail_soup = BeautifulSoup(resp_text, features="html.parser")
                except Exception:
                    detail_soup = BeautifulSoup(detail_resp.content, features="html.parser")

                # Description from detail page if not already found
                if not listing.description:
                    desc_section = detail_soup.find('section', {'data-testid': 'description'})
                    if desc_section:
                        description = desc_section.get_text(' ', strip=True)
                        if not description or len(description) < 10:
                            desc_start = resp_text.find('data-testid="description"')
                            if desc_start >= 0:
                                tag_end = resp_text.find('>', desc_start)
                                if tag_end >= 0:
                                    desc_end = resp_text.find('</section>', tag_end)
                                    if desc_end >= 0:
                                        desc_html = resp_text[tag_end + 1:desc_end]
                                        desc_clean = re.sub(r'<[^>]+>', ' ', desc_html)
                                        description = re.sub(r'\s+', ' ', desc_clean).strip()
                        listing.description = description[:500] if description else ""

                # Date: try meta tags first
                meta_date = detail_soup.find('meta', attrs={'property': 'article:published_time'})
                if meta_date and meta_date.get('content'):
                    listing.date_posted = _parse_dba_date(meta_date.get('content'))

                if not listing.date_posted:
                    for meta_tag in detail_soup.find_all('meta'):
                        content = meta_tag.get('content', '')
                        if content and re.match(r'\d{4}-\d{2}-\d{2}', content):
                            listing.date_posted = _parse_dba_date(content)
                            break

                if not listing.date_posted:
                    date_match = re.search(
                        r'(?:Sidst redigeret|Oprettet|Dato|Postet)\s*:?\s*(\d{1,2}\.\d{1,2}\.\d{4}\s*(?:kl\.\s*)?\d{1,2}:\d{2})'
                        r'|(\d{1,2}\.\d{1,2}\.\d{4}\s*(?:kl\.\s*)?\d{1,2}:\d{2})',
                        resp_text,
                        re.IGNORECASE,
                    )
                    if date_match:
                        listing.date_posted = _parse_dba_date((date_match.group(1) or date_match.group(2)).strip())

                if not listing.date_posted:
                    for time_el in detail_soup.find_all("time"):
                        datetime_val = time_el.get("datetime")
                        if datetime_val:
                            listing.date_posted = _parse_dba_date(datetime_val)
                            break
                        text = time_el.get_text(strip=True)
                        if text and len(text) > 5:
                            listing.date_posted = _parse_dba_date(text)
                            break

                if not listing.date_posted:
                    date_match = re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', resp_text)
                    if date_match:
                        listing.date_posted = _parse_dba_date(date_match.group(0))

            except (httpx.TimeoutException, httpx.HTTPStatusError):
                pass
            except Exception:
                pass

    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
        """
        Scrape DBA listings using the recommerce URL structure.
        Search page: https://www.dba.dk/recommerce/forsale/search?q=...
        Detail pages are fetched concurrently (semaphore of _DETAIL_CONCURRENCY).
        """
        url = f"https://www.dba.dk/recommerce/forsale/search?q={urllib.parse.quote_plus(query)}"
        listings = []

        async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=config.SCRAPER_TIMEOUT) as s:
            try:
                resp = await s.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")

                cards = soup.select('a[href*="/recommerce/forsale/item/"]')

                filtered_cards = []
                for card in cards:
                    parent = card.parent
                    if parent and parent.name in ('div', 'article', 'li', 'section'):
                        if len(parent.get_text(strip=True)) > 10:
                            filtered_cards.append(card)

                self.log_debug(f"[blue]DBA: Found {len(cards)} cards, {len(filtered_cards)} after filtering[/blue]")

                if not filtered_cards:
                    filtered_cards = cards
                    self.log_debug("[blue]DBA: Using all cards as fallback[/blue]")

                cards = filtered_cards[:max_results]
                seen_urls = set()

                # Phase 1: parse cards (CPU-only, no network)
                for i, card in enumerate(cards):
                    href = card.get("href", "")
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # Title
                    title = card.get_text(strip=True)
                    self.log_debug(f"[dim]DBA card {i} text: '{title}'[/dim]")

                    if not title:
                        parent = card.parent
                        if parent:
                            title_el = parent.select_one('h2, h3, h4, [class*="title"], [class*="name"], [data-testid*="title"]')
                            if title_el:
                                title = title_el.get_text(strip=True)
                                self.log_debug(f"[dim]DBA found in parent: '{title}'[/dim]")
                            else:
                                title = parent.get_text(strip=True)[:200]
                                self.log_debug(f"[dim]DBA from parent text: '{title[:80]}'[/dim]")

                    if not title or len(title) < 2:
                        match = re.search(r'/item/(\d+)', href)
                        if match:
                            title = f"DBA Item {match.group(1)}"
                        else:
                            continue

                    title_parts = re.split(r'\d+\s*(kr|dkk|eur|€|\$)|(kr|dkk|eur|€|\$)\s*\d+|\d+[.,\s]\d+\s*(kr|dkk|eur|€|\$)', title, flags=re.IGNORECASE)
                    title = title_parts[0].strip() if title_parts else title

                    # Price
                    price_el = None
                    price_text = ""

                    for search_area in [card, card.parent if card.parent else None, None]:
                        if not search_area:
                            continue

                        price_el = search_area.select_one('[class*="price"], [class*="pris"], [class*="amount"], [class*="beløb"]')
                        if price_el:
                            price_text = price_el.get_text(strip=True)
                            self.log_debug(f"[blue]DBA price class match: {price_text}[/blue]")
                            break

                        price_el = search_area.select_one('[data-price], [data-amount]')
                        if price_el:
                            price_text = price_el.get('data-price', '') or price_el.get('data-amount', '') or price_el.get_text(strip=True)
                            self.log_debug(f"[blue]DBA price data attr: {price_text}[/blue]")
                            break

                        for tag in search_area.find_all(['span', 'div', 'p', 'strong', 'b', 'price']):
                            text = tag.get_text(strip=True)
                            if re.search(r'\d{1,3}[\.\s,]\d{3,}(\s*(kr|dkk))?', text, re.IGNORECASE):
                                price_el = tag
                                price_text = text
                                self.log_debug(f"[blue]DBA price pattern match: {price_text}[/blue]")
                                break

                        if price_el:
                            break

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

                    if price < 10 and price > 0:
                        self.log_debug(f"[yellow]DBA suspicious low price: {price} for {title[:50]}[/yellow]")

                    if self.debug:
                        if price_el:
                            self.log_debug(f"[dim]DBA price: {price_text} -> {price}[/dim]")
                        else:
                            self.log_debug(f"[yellow]DBA no price found for {title}[/yellow]")

                    # Partial description from card
                    description = ""
                    if card.parent:
                        desc_el = card.parent.select_one('[class*="description"], [class*="excerpt"], [class*="summary"]')
                        if desc_el:
                            description = desc_el.get_text(strip=True)[:300]

                    # Images
                    images = []
                    for img_el in card.find_all('img', src=True):
                        src = img_el.get('src', '').strip()
                        if src and not src.startswith('data:'):
                            if src.startswith('/'):
                                src = f"https://www.dba.dk{src}"
                            images.append(src)
                    if not images and card.parent:
                        for img_el in card.parent.find_all('img', src=True):
                            src = img_el.get('src', '').strip()
                            if src and not src.startswith('data:'):
                                if src.startswith('/'):
                                    src = f"https://www.dba.dk{src}"
                                images.append(src)
                    if images:
                        images = list(dict.fromkeys(images))[:3]

                    full_url = f"https://www.dba.dk{href}" if href.startswith("/") else href

                    listings.append(Listing(
                        title=title,
                        price=price,
                        currency="DKK",
                        url=full_url,
                        description=description,
                        platform=self.platform,
                        date_posted="",
                        images=images,
                    ))

                # Phase 2: fetch all detail pages concurrently
                if listings:
                    sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
                    await asyncio.gather(
                        *[self._fetch_detail(s, listing, sem) for listing in listings],
                        return_exceptions=True,
                    )

            except Exception as e:
                console.print(f"[red]DBA error: {e}[/red]")

        console.print(f"[green]DBA:[/green] {len(listings)} listings found")
        return listings
