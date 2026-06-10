"""
LLM filter - LLM-based relevance filtering for listings.

Implements BaseFilter for the modular pipeline.
"""

import asyncio
import json
import random
from typing import List, Dict, Any

import httpx
from rich.console import Console

from models import Listing
from llm import LLMClient, get_client
from utils import extract_json
from core.module import ModuleType
from core.logging import get_logger
from filters.base import BaseFilter
import config

console = Console()
logger = get_logger(__name__, module_name="filters.llm_filter")


class LLMFilter(BaseFilter):
    """LLM-based relevance filtering using Gemini or Mistral."""
    
    name = "llm-filter"
    module_type = ModuleType.FILTER
    version = "1.0.0"
    
    def __init__(self, llm_backend: str = "gemini", debug: bool = False):
        """
        Initialize the filter.
        
        Args:
            llm_backend: The LLM backend to use (gemini or mistral)
            debug: Whether to print debug information
        """
        super().__init__()
        self.llm_backend = llm_backend
        self.debug = debug
        self._llm_client = None
    
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
        
        try:
            self._llm_client = get_client(self.llm_backend)
            logger.info("LLMFilter initialized", extra={"llm_backend": self.llm_backend})
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
        return self._initialized and self._llm_client is not None
    
    async def filter(self, listings: List[Any], query: str, context: Dict[str, Any]) -> List[Any]:
        """
        Filters listings for relevance using LLM.
        Processes batches sequentially to avoid rate limits.
        
        Args:
            listings: List of listings to filter
            query: The user's search query
            context: Additional context
            
        Returns:
            Filtered list of relevant listings
        """
        batch_size = context.get("batch_size", config.BATCH_SIZE)
        delay_between_batches = context.get("delay_between_batches", config.DELAY_BETWEEN_BATCHES)
        max_retries = context.get("max_retries", config.MAX_RETRIES)
        
        async def judge_batch(batch: list, user_query: str) -> None:
            items_json = json.dumps(
                [
                    {"id": i, "title": getattr(l, 'title', ''), "description": getattr(l, 'description', '')[:400]}
                    for i, l in enumerate(batch)
                ],
                ensure_ascii=False,
            )

            prompt = f"""You are a shopping assistant. The user is looking for: "{user_query}"

Below is a JSON list of second-hand listings. For each one decide:
- relevant: true or false
- reason: 2-3 words maximum explaining why (e.g., "not phone", "wrong brand", "accessory only")

A listing is relevant if it matches the user's query closely in terms of product type, brand, or features.
Eg. if the user is looking for "iPhone 12 with good camera", a listing titled "iPhone 12 Pro Max - Excellent Camera" would be relevant, while "iPhone 12 case" would be not relevant with reason "case only".

Return ONLY a JSON object in this exact format:
{{"results": [{{"id": 0, "relevant": true, "reason": "..."}}]}}

Listings:
{items_json}"""

            for attempt in range(max_retries):
                try:
                    raw_response = await self._llm_client.chat(prompt)
                    parsed_response = extract_json(raw_response)

                    if isinstance(parsed_response, dict):
                        verdicts = parsed_response.get("results", [])
                    elif isinstance(parsed_response, list):
                        verdicts = parsed_response
                    else:
                        verdicts = []

                    for verdict in verdicts:
                        idx = verdict.get("id")
                        if idx is not None and 0 <= idx < len(batch):
                            batch[idx].relevant = verdict.get("relevant", False)
                            batch[idx].relevance_reason = verdict.get("reason", "")
                            # Print discarded listings immediately
                            if not batch[idx].relevant and batch[idx].relevance_reason:
                                console.print(f"  [red]✗ {getattr(batch[idx], 'title', 'Unknown')}: {batch[idx].relevance_reason}[/red]")

                    return

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait_time = (2 ** attempt) + random.uniform(1, 3)
                        console.print(f"[yellow]Rate limited. Waiting {wait_time:.1f}s before retrying...[/yellow]")
                        await asyncio.sleep(wait_time)
                    else:
                        console.print(f"[red]HTTP error: {e}[/red]")
                        break

                except Exception as e:
                    if attempt == max_retries - 1:
                        console.print(f"[red]Filter batch error: {e} — keeping batch as-is[/red]")
                        for listing in batch:
                            listing.relevant = True
                    else:
                        wait_time = (2 ** attempt) + random.uniform(1, 3)
                        console.print(f"[yellow]Retrying in {wait_time:.1f}s due to error: {e}[/yellow]")
                        await asyncio.sleep(wait_time)

        batches = [listings[i:i + batch_size] for i in range(0, len(listings), batch_size)]
        total_batches = len(batches)
        total_discarded = 0

        sem = asyncio.Semaphore(3)  # max 3 concurrent LLM calls

        async def judge_batch_guarded(batch: list, batch_num: int) -> None:
            async with sem:
                console.print(f"Judging batch {batch_num}/{total_batches} ({len(batch)} items)...")
                await judge_batch(batch, query)

        await asyncio.gather(*[
            judge_batch_guarded(batch, i + 1) for i, batch in enumerate(batches)
        ])

        if not any(getattr(l, 'relevant', False) for l in listings):
            console.print("[yellow]No relevant listings found. Marking all as relevant as fallback.[/yellow]")
            for listing in listings:
                listing.relevant = True
                listing.relevance_reason = "Fallback: No relevant listings identified by the model."

        relevant_listings = [listing for listing in listings if getattr(listing, 'relevant', False)]
        if total_discarded > 0:
            console.print(f"[bold yellow]{total_discarded} listings discarded[/bold yellow]")
        console.print(f"[bold green]{len(relevant_listings)} relevant listings kept[/bold green]\n")
        
        logger.info("LLM filtering complete", 
                   extra={"kept": len(relevant_listings), "discarded": total_discarded})
        
        return relevant_listings
