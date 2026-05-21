"""
Ranker - scores and ranks listings based on multiple factors.
"""

import json

from rich.console import Console

from models import Listing
from llm import LLMClient
from utils import extract_json
from core.logging import get_logger

console = Console()
logger = get_logger(__name__, module_name="ranker")


class Ranker:
    """Scores and ranks listings based on value and relevance."""
    
    def __init__(self, llm_client: LLMClient, debug: bool = False, no_score: bool = False):
        """
        Initialize the ranker.
        
        Args:
            llm_client: The LLM client to use for scoring
            debug: Whether to print debug information
            no_score: Whether to skip LLM scoring and sort by price instead
        """
        self.llm_client = llm_client
        self.debug = debug
        self.no_score = no_score
    
    async def score_and_rank(self, listings: list[Listing], user_query: str) -> list[Listing]:
        """
        Score each listing 1–10 based on price, relevance, description quality, and review quality.
        Falls back to price-based sort on error.
        
        Args:
            listings: List of listings to score
            user_query: The user's search query
            
        Returns:
            Ranked list of listings
        """
        if not listings:
            return listings

        # Skip scoring if disabled
        if self.no_score:
            console.print("[bold cyan]Step 6: Sorting by price (--no-score flag)[/bold cyan]")
            # Sort by price ascending (cheapest first)
            listings.sort(key=lambda l: l.price if l.price > 0 else float('inf'))
            for listing in listings:
                listing.score = 10.0 - min(9.0, listing.price / 100)  # Rough score based on price
            console.print()
            return listings

        # Warn about suspiciously high prices
        for listing in listings:
            if listing.price > 10000:
                console.print(f"[yellow]⚠️  Suspicious price: {listing.title} ({listing.platform}): {listing.price} {listing.currency}[/yellow]")

        items_json = json.dumps(
            [
                {
                    "id":             i,
                    "title":          l.title,
                    "description":    l.description,
                    "price":          l.price,
                    "currency":       l.currency,
                    "platform":       l.platform,
                    "review_summary": l.review_summary,
                }
                for i, l in enumerate(listings)
            ],
            ensure_ascii=False,
        )

        prompt = f"""The user is looking for: "{user_query}"

Score each of the following second-hand listings. First, give a score from 1 to 10 for each of these categories (1 = poor, 10 = excellent):
- Price (compared to typical market price for this item)
- Value for money (price vs. typical market price)
- How well it matches the user's stated need
- Condition and quality indicators from the title AND description (mentions of new/unused, damage, original packaging, accessories included, etc.)
- Review quality (positive reviews = higher score)
Then, provide an overall score from 1 to 10 for each listing based on these factors.

Pay special attention to the description field which contains important details about the item's condition and what's included.

Return ONLY a JSON object:
{{"scores": [{{"id": 0, "score": 7.5, "reason": "one sentence"}}]}}

Listings:
{items_json}"""

        console.print("[bold cyan]Step 6: Scoring and ranking...[/bold cyan]")
        try:
            raw    = await self.llm_client.chat(prompt, temperature=0.1)
            parsed = extract_json(raw)
            scores = parsed.get("scores", []) if isinstance(parsed, dict) else []

            for s in scores:
                idx = s.get("id")
                if idx is not None and 0 <= idx < len(listings):
                    listings[idx].score = float(s.get("score", 0))
                    listings[idx].score_reason = s.get("reason", "")
        except Exception as e:
            console.print(f"[red]Scoring error: {e} — falling back to price sort[/red]")
            # Fallback: score inversely by price (cheaper = higher score)
            prices = [l.price for l in listings if l.price > 0]
            if prices:
                max_p = max(prices)
                for l in listings:
                    l.score = round(10 * (1 - l.price / max_p), 1) if l.price > 0 else 5.0

        listings.sort(key=lambda l: l.score, reverse=True)
        return listings
