"""
Model extractor - extracts product model names from listings.

Implements BaseProcessor for the modular pipeline.
"""

import asyncio
import json
from typing import List, Dict, Any

from rich.console import Console

from models import Listing
from llm import get_client
from utils import extract_json
from core.module import ModuleType
from core.logging import get_logger
from processors.base import BaseProcessor
import config

console = Console()
logger = get_logger(__name__, module_name="processors.model_extractor")


class ModelExtractor(BaseProcessor):
    """Extracts product model names from listing titles."""
    
    name = "model-extractor"
    module_type = ModuleType.PROCESSOR
    version = "1.0.0"
    
    def __init__(self, llm_backend: str = "gemini", debug: bool = False):
        """
        Initialize the extractor.
        
        Args:
            llm_backend: The LLM backend to use (gemini or mistral)
            debug: Whether to print debug information
        """
        super().__init__()
        self.llm_backend = llm_backend
        self.debug = debug
        self._llm_client = None
        self._delay = 4.0  # Default delay
    
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
        self._delay = config.get("review_delay", 4.0)
        
        try:
            self._llm_client = get_client(self.llm_backend)
            logger.info("ModelExtractor initialized", extra={"llm_backend": self.llm_backend})
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

    async def _process_batch(self, batch: List[Any]) -> None:
        """
        Process a single batch of listings.
        
        Args:
            batch: List of listings in this batch
        """
        items_json = json.dumps(
            [{"id": j, "title": listing.title, "description": getattr(listing, 'description', '')[:200]} 
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
            raw = await self._llm_client.chat(prompt)
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
            logger.error("Model extraction error", extra={"error": str(e)})

    async def process(self, listings: List[Any], context: Dict[str, Any]) -> List[Any]:
        """
        Extract product models from listings.
        
        Args:
            listings: List of listings to process
            context: Additional context
            
        Returns:
            Processed list of listings with model names
        """
        if not listings:
            return listings
        
        batch_size = max(10, context.get("batch_size", context.get("BATCH_SIZE", 30)))
        
        # Create batches
        batches = [
            listings[i : i + batch_size] 
            for i in range(0, len(listings), batch_size)
        ]
        
        # Process all batches concurrently
        await asyncio.gather(*[
            self._process_batch(batch) 
            for batch in batches
        ])
        
        return listings
