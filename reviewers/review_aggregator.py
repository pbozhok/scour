"""
Review aggregator module - searches for and summarizes reviews for listings.

Implements BaseReviewer for the modular pipeline.
"""

import asyncio
from typing import List, Dict, Any
from rich.console import Console

from models import Listing
from llm import get_client
from utils import extract_json, normalize_model_name
from reviewers.search import ReviewSearcher
from core.module import ModuleType, PipelineContext
from core.logging import get_logger
from reviewers.base import BaseReviewer

console = Console()
logger = get_logger(__name__, module_name="reviewers.review_aggregator")


class ReviewAggregator(BaseReviewer):
    """Aggregates reviews for product models and assigns summaries to listings."""
    
    name = "review-aggregator"
    module_type = ModuleType.REVIEWER
    version = "1.0.0"
    
    def __init__(self, llm_backend: str = "gemini", debug: bool = False):
        """
        Initialize the aggregator.
        
        Args:
            llm_backend: The LLM backend to use (gemini or mistral)
            debug: Whether to print debug information
        """
        super().__init__()
        self.llm_backend = llm_backend
        self.debug = debug
        self.searcher = ReviewSearcher()
        self._llm_client = None
        self._delay = 4.0
    
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
            logger.info("ReviewAggregator initialized", extra={"llm_backend": self.llm_backend})
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
    
    async def review(self, listings: List[Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and summarize reviews for listings.
        
        Args:
            listings: List of listings to review
            context: Additional context
            
        Returns:
            Dictionary with review information
        """
        # This method signature is required by BaseReviewer but we use execute() instead
        # Return empty dict as we handle reviews in execute()
        return {}
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the review aggregator module.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with review summaries added to listings
        """
        if not self._initialized:
            self.initialize(context.config)
        
        listings = context.get_listings()
        
        try:
            await self._aggregate_reviews(listings)
            context.set_metadata(f"{self.name}_reviewed", len(listings))
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="REVIEW_ERROR",
                message=str(e),
                context={"listing_count": len(listings), "query": context.query}
            )
        
        return context
    
    async def _search_reviews_for_models(self, listings: list[Listing]) -> dict[str, list[dict]]:
        """
        Search reviews for each unique product model only once.
        Returns a dict mapping normalized_model -> list of review dicts.
        Deduplicates models to avoid redundant searches.
        """
        seen_normalized = set()
        unique_models = []
        
        for listing in listings:
            if hasattr(listing, 'product_model') and listing.product_model:
                normalized = normalize_model_name(listing.product_model)
                if normalized and normalized not in seen_normalized:
                    unique_models.append((listing.product_model, normalized))
                    seen_normalized.add(normalized)
        
        if not unique_models:
            return {}
        
        original_models = [m[0] for m in unique_models]
        console.print(f"  [dim]Searching reviews for {len(unique_models)} unique model(s): {', '.join(original_models)}[/dim]")
        
        results = await asyncio.gather(*[self.searcher.search_reviews(model[0]) for model in unique_models])
        
        reviews_cache = {}
        for (original, normalized), reviews in zip(unique_models, results):
            reviews_cache[normalized] = reviews
        
        return reviews_cache
    
    async def _generate_summary_for_model(self, model: str, raw_reviews: list[dict]) -> dict[str, Any]:
        """Generate a summary for a specific model's reviews."""
        if not raw_reviews:
            return {"summary": "No reviews found.", "links": []}
        
        review_links = [r["url"] for r in raw_reviews if r.get("url")]
        
        review_text = "\n\n".join(
            f"Source: {r['title']}\n{r['snippet']}" for r in raw_reviews
        )

        prompt = f"""Based on the review excerpts below for "{model}",
write a 2-3 sentence summary covering:
1. Key strengths
2. Main weaknesses
3. Who it is best suited for

Be concise and factual. Do not invent information not present in the excerpts.

Return ONLY a JSON object:
{{"summary": "your summary here"}}

Review excerpts:
{review_text}"""

        try:
            raw = await self._llm_client.chat(prompt, temperature=0.2)
            parsed = extract_json(raw)
            if isinstance(parsed, dict):
                summary = parsed.get("summary", "Summary unavailable.")
            else:
                summary = "Summary unavailable."
        except Exception as e:
            summary = f"Error generating summary: {e}"
        
        return {"summary": summary, "links": review_links}
    
    async def _aggregate_reviews(self, listings: list[Listing]) -> None:
        """Search reviews per unique model, generate summaries, then assign to listings."""
        console.print("[bold cyan]Aggregating reviews...[/bold cyan]")
        
        reviews_cache = await self._search_reviews_for_models(listings)
        
        summary_cache = {}
        normalized_models = set()
        
        for listing in listings:
            if hasattr(listing, 'product_model') and listing.product_model:
                normalized = normalize_model_name(listing.product_model)
                if normalized:
                    normalized_models.add(normalized)
        
        for normalized_model in normalized_models:
            original_model = None
            for listing in listings:
                if hasattr(listing, 'product_model') and listing.product_model:
                    if normalize_model_name(listing.product_model) == normalized_model:
                        original_model = listing.product_model
                        break
            
            if original_model:
                summary_cache[normalized_model] = await self._generate_summary_for_model(
                    original_model, 
                    reviews_cache.get(normalized_model, [])
                )
        
        for listing in listings:
            if hasattr(listing, 'product_model') and listing.product_model:
                normalized = normalize_model_name(listing.product_model)
                if normalized and normalized in summary_cache:
                    summary_data = summary_cache[normalized]
                    listing.review_summary = summary_data["summary"]
                    listing.review_links = summary_data["links"]
        
        console.print(f"  Done for {len(listings)} listings ({len(normalized_models)} unique model(s))\n")
