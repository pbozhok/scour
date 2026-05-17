"""
Model extractor - extracts product model names from listings.
"""

import asyncio
import json

from rich.console import Console

from models import Listing
from llm import LLMClient
from utils import extract_json
import config

console = Console()


class ModelExtractor:
    """Extracts product model names from listing titles."""
    
    def __init__(self, llm_client: LLMClient, debug: bool = False):
        """
        Initialize the extractor.
        
        Args:
            llm_client: The LLM client to use for extraction
            debug: Whether to print debug information
        """
        self.llm_client = llm_client
        self.debug = debug
    
    async def extract_models(
        self,
        listings: list[Listing],
        delay: float = config.REVIEW_DELAY,
    ) -> None:
        """
        Extracts product model names from listing titles.
        Processes in batches with delays between batches.
        
        Args:
            listings: List of listings to extract models from
            delay: Delay in seconds between batches
        """
        if not listings:
            return

        batch_size = 10

        for i in range(0, len(listings), batch_size):
            batch = listings[i : i + batch_size]

            items_json = json.dumps(
                [{"id": j, "title": listing.title, "description": listing.description[:200]} 
                 for j, listing in enumerate(batch)],
                ensure_ascii=False,
            )

            prompt = f"""From each listing below, extract the most specific product model name
suitable for a Google search to find professional reviews.
Use both the title and description to identify the model.
If you cannot determine a specific model, return an empty string.

Return ONLY this JSON format:
{{"results": [{{"id": 0, "model": "..."}}]}}

Listings:
{items_json}"""

            try:
                raw    = await self.llm_client.chat(prompt)
                parsed = extract_json(raw)
                models = []

                if isinstance(parsed, dict):
                    models = parsed.get("results", [])
                elif isinstance(parsed, list):
                    models = parsed

                for m in models:
                    idx = m.get("id")
                    if idx is not None and 0 <= idx < len(batch):
                        batch[idx].product_model = m.get("model", "")

            except Exception as e:
                console.print(f"[red]Model extraction error: {e}[/red]")

            if i + batch_size < len(listings):
                await asyncio.sleep(delay)
