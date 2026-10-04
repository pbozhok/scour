"""
Vinted scraper - for vinted.dk second-hand listings.

The public /api/v2 endpoints Vinted used to expose now return 404, so this
scrapes the server-rendered catalog page instead. Vinted ships its React
Server Component payload inline, which carries an accessibility label per
item holding title, brand, condition, size and both prices.
"""

import asyncio
import re

import httpx
from rich.console import Console

from models import Listing
from scrapers.base import BaseScraper
import config
from core.logging import get_logger
from core.module import ModuleType

console = Console()
logger = get_logger(__name__, module_name="scrapers.vinted")

BASE_URL = "https://www.vinted.dk"
PER_PAGE = 96  # items the catalog page renders per request

# RSC payload is JSON escaped into the HTML; unescaped it looks like
#   "accessibilityLabel":"<label>","badge":...,"itemId":"<id>"
_ITEM_RE = re.compile(r'"accessibilityLabel":"(.*?)","badge".*?"itemId":"(\d+)"')

# Danish labels inside the accessibility string
_BRAND_RE = re.compile(r"Varem(?:æ|ae)rke:\s*([^,]+)")
_COND_RE = re.compile(r"Artiklens stand:\s*([^,]+)")
_SIZE_RE = re.compile(r"St(?:ø|oe)rrelse:\s*([^,]+)")
_PRICE_RE = re.compile(r"([\d.,]+)\s*kr")


def _to_float(raw: str) -> float:
    """Convert a Danish-formatted price ('1.095,00' or '1095.00') to float."""
    raw = raw.strip()
    if "," in raw:  # 1.095,00 -> 1095.00
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _parse_label(label: str) -> dict:
    """Pull the structured fields out of one accessibility label."""
    brand = _BRAND_RE.search(label)
    cond = _COND_RE.search(label)
    size = _SIZE_RE.search(label)
    prices = [_to_float(p) for p in _PRICE_RE.findall(label)]

    # The label starts with the seller's own title, up to the first field.
    title = label.split(", Varem")[0].strip() or "Unknown"

    return {
        "title": title,
        "brand": brand.group(1).strip() if brand else "",
        "condition": cond.group(1).strip() if cond else "",
        "size": size.group(1).strip() if size else "",
        # first price is the item, second (when present) includes buyer protection
        "price": prices[0] if prices else 0.0,
        "total_price": prices[1] if len(prices) > 1 else (prices[0] if prices else 0.0),
    }


class VintedScraper(BaseScraper):
    """Scraper for Vinted.dk second-hand listings."""

    name = "vinted-scraper"
    module_type = ModuleType.SCRAPER
    version = "2.0.0"
    platform = "Vinted"

    def _fetch(self, query: str, pages: int) -> list[str]:
        """Fetch catalog pages, returning raw HTML for each."""
        htmls = []
        with httpx.Client(
            http2=True,
            follow_redirects=True,
            timeout=config.SCRAPER_TIMEOUT,
            headers={
                "User-Agent": config.HEADERS["User-Agent"],
                "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
            },
        ) as client:
            client.get(BASE_URL + "/")  # seeds anon_id / access_token_web cookies
            for page in range(1, pages + 1):
                resp = client.get(
                    BASE_URL + "/catalog",
                    params={"search_text": query, "page": page},
                )
                if resp.status_code != 200:
                    self.log_debug(
                        f"[yellow]Vinted page {page}: HTTP {resp.status_code}[/yellow]"
                    )
                    break
                htmls.append(resp.text)
        return htmls

    async def scrape(
        self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS
    ) -> list[Listing]:
        """Scrape Vinted listings from the catalog page's inline RSC payload."""
        listings: list[Listing] = []
        pages = max(1, -(-max_results // PER_PAGE))  # ceil

        try:
            htmls = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch, query, pages
            )
        except Exception as e:
            self.log_debug(f"[yellow]Vinted fetch error: {e}[/yellow]")
            htmls = []

        seen: set[str] = set()
        for html in htmls:
            for label, item_id in _ITEM_RE.findall(html.replace('\\"', '"')):
                if item_id in seen or len(listings) >= max_results:
                    continue
                seen.add(item_id)

                f = _parse_label(label)
                # Size and condition have no home on Listing, so surface them
                # in the description where the filter and scorer can read them.
                desc = " | ".join(
                    p
                    for p in (
                        f"Size: {f['size']}" if f["size"] else "",
                        f"Condition: {f['condition']}" if f["condition"] else "",
                        f"Brand: {f['brand']}" if f["brand"] else "",
                        f"Total incl. buyer protection: {f['total_price']:.2f} DKK",
                    )
                    if p
                )

                listings.append(
                    Listing(
                        title=f["title"],
                        price=f["price"],
                        currency="DKK",
                        url=f"{BASE_URL}/items/{item_id}",
                        description=desc,
                        platform=self.platform,
                    )
                )

        if not listings:
            self.log_debug("[yellow]Vinted: no items parsed from catalog[/yellow]")

        kept = self.filter_by_relevance(listings, query)
        if len(kept) < len(listings):
            self.log_debug(
                f"[yellow]Vinted: dropped {len(listings) - len(kept)} loose matches[/yellow]"
            )
        console.print(f"[green]Vinted:[/green] {len(kept)} listings found")
        return kept
