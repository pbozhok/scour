"""
Ranker module - scores and ranks listings based on multiple factors.

Implements Module interface for the modular pipeline.
"""

import asyncio
import json
from typing import List, Dict, Any

from rich.console import Console

from models import Listing
from llm import get_client
from utils import extract_json
from core.module import Module, ModuleType, PipelineContext
from core.logging import get_logger

console = Console()
logger = get_logger(__name__, module_name="ranker")


class RankerModule(Module):
    """Scores and ranks listings based on value and relevance."""
    
    name = "ranker"
    module_type = ModuleType.RANKER
    version = "1.0.0"
    
    def __init__(self, llm_backend: str = "gemini", debug: bool = False, no_score: bool = False):
        """
        Initialize the ranker.
        
        Args:
            llm_backend: The LLM backend to use (gemini or mistral)
            debug: Whether to print debug information
            no_score: Whether to skip LLM scoring and sort by price instead
        """
        self.llm_backend = llm_backend
        self.debug = debug
        self.no_score = no_score
        self._llm_client = None
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization succeeded
        """
        self._initialized = True
        self.llm_backend = config.get("llm_backend", "gemini")
        self.debug = config.get("debug", False)
        self.no_score = config.get("skip_score", False)
        
        try:
            self._llm_client = get_client(self.llm_backend)
            logger.info("Ranker initialized", extra={"llm_backend": self.llm_backend})
            return True
        except Exception as e:
            logger.error("Failed to initialize LLM client", extra={"error": str(e)})
            return False
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        if self.no_score:
            return self._initialized
        return self._initialized and self._llm_client is not None
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        self._initialized = False
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the ranker module.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with listings scored and ranked
        """
        if not self._initialized:
            self.initialize(context.config)
        
        listings = context.get_listings()
        
        # Use cleaned query from metadata if available, otherwise use context.query
        query = context.get_metadata("cleaned_query", default=context.query)
        
        try:
            ranked = await self.score_and_rank(listings, query)
            context.listings = ranked
            context.set_metadata(f"{self.name}_ranked", len(ranked))
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="RANKING_ERROR",
                message=str(e),
                context={"listing_count": len(listings), "query": query}
            )
        
        return context
    
    async def score_and_rank(self, listings: list[Listing], user_query: str) -> list[Listing]:
        """
        Score each listing 1-10 based on price, relevance, description quality, and review quality.
        Falls back to a simple price-based sort on error.
        
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
            console.print("[bold cyan]Scoring: Sorting by price (--no-score flag)[/bold cyan]")
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
        
        _BATCH = 30  # items per scoring call

        score_prompt = (
            f'The user is looking for: "{user_query}"\n\n'
            "Score each listing 1-10 based on: value for money, how well it matches "
            "the user's need, condition indicators (new/unused/damage), and review quality.\n\n"
            'Return ONLY: {"scores": [{"id": 0, "score": 7.5, "reason": "one sentence"}]}\n\n'
            "Listings:\n"
        )

        async def score_batch(batch: list, offset: int) -> None:
            items_json = json.dumps(
                [
                    {
                        "id": offset + i,
                        "title": l.title,
                        "description": (l.description or "")[:200],
                        "price": l.price,
                        "currency": l.currency,
                        "platform": l.platform,
                        "review_summary": getattr(l, 'review_summary', ''),
                    }
                    for i, l in enumerate(batch)
                ],
                ensure_ascii=False,
            )
            try:
                raw = await self._llm_client.chat(score_prompt + items_json, temperature=0.1)
                parsed = extract_json(raw)
                scores = parsed.get("scores", []) if isinstance(parsed, dict) else []
                for s in scores:
                    idx = s.get("id")
                    if idx is not None and 0 <= idx < len(listings):
                        listings[idx].score = float(s.get("score", 0))
                        listings[idx].score_reason = s.get("reason", "")
            except Exception as e:
                console.print(f"[red]Scoring error: {e} — falling back to price sort[/red]")

        console.print("[bold cyan]Scoring and ranking...[/bold cyan]")
        batches = [(listings[i:i + _BATCH], i) for i in range(0, len(listings), _BATCH)]
        await asyncio.gather(*[score_batch(b, off) for b, off in batches])

        # Fallback for any listing that wasn't scored
        prices = [l.price for l in listings if l.price > 0]
        max_p = max(prices) if prices else 1
        for l in listings:
            if not l.score:
                l.score = round(10 * (1 - l.price / max_p), 1) if l.price > 0 else 5.0

        listings.sort(key=lambda l: l.score, reverse=True)
        return listings
