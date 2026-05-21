"""
Review search - finds reviews for products from various sources.
"""

import urllib.parse

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

import config
from core.logging import get_logger

console = Console()
logger = get_logger(__name__, module_name="reviewers.search")


class ReviewSearcher:
    """Searches for reviews from various sources (DuckDuckGo, SerpAPI)."""
    
    async def search_duckduckgo(self, model: str, max_results: int = 3) -> list[dict]:
        """
        Free fallback: scrapes DuckDuckGo HTML search results.
        Targets review-rich sites: Reddit, Notebookcheck, RTINGS, Wirecutter, GSMArena.
        
        Args:
            model: The product model to search for
            max_results: Maximum number of results
            
        Returns:
            List of review results
        """
        query = (
            f"{model} review site:reddit.com OR site:notebookcheck.net "
            "OR site:rtings.com OR site:wirecutter.com OR site:gsmarena.com"
        )
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
        results = []

        async with httpx.AsyncClient(headers=config.HEADERS, follow_redirects=True, timeout=20) as s:
            try:
                resp = await s.get(url)
                soup = BeautifulSoup(resp.text, "html.parser")

                for result in soup.select(".result")[:max_results]:
                    title_el   = result.select_one(".result__title")
                    snippet_el = result.select_one(".result__snippet")
                    link_el    = result.select_one(".result__url")

                    title   = title_el.get_text(strip=True)   if title_el   else ""
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    link    = link_el.get_text(strip=True)    if link_el    else ""

                    if title:
                        results.append({
                            "title":   title,
                            "snippet": snippet,
                            "url":     link if link.startswith("http") else f"https://{link}",
                        })
            except Exception as e:
                console.print(f"[red]DuckDuckGo search error for '{model}': {e}[/red]")

        return results

    async def search_serpapi(self, model: str, max_results: int = 3) -> list[dict]:
        """
        SerpAPI search (requires SERPAPI_KEY env var).
        Free tier: 100 searches/month.
        
        Args:
            model: The product model to search for
            max_results: Maximum number of results
            
        Returns:
            List of review results
        """
        query = f"{model} review"
        url   = "https://serpapi.com/search"
        results = []

        async with httpx.AsyncClient(timeout=20) as s:
            try:
                resp = await s.get(url, params={
                    "q":       query,
                    "api_key": config.SERPAPI_KEY,
                    "num":     max_results,
                })
                data = resp.json()

                for r in data.get("organic_results", [])[:max_results]:
                    results.append({
                        "title":   r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "url":     r.get("link", ""),
                    })
            except Exception as e:
                console.print(f"[red]SerpAPI error for '{model}': {e}[/red]")

        return results

    async def search_reviews(self, model: str) -> list[dict]:
        """
        Route to SerpAPI if key is available, otherwise DuckDuckGo.
        
        Args:
            model: The product model to search for
            
        Returns:
            List of review results
        """
        if config.SERPAPI_KEY:
            return await self.search_serpapi(model)
        return await self.search_duckduckgo(model)
