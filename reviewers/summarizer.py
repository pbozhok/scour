"""
Review summarizer - generates summaries of product reviews.
"""

import asyncio
from typing import Any

from rich.console import Console

from models import Listing
from llm import LLMClient
from utils import extract_json, normalize_model_name
from reviewers.search import ReviewSearcher

console = Console()


class ReviewSummarizer:
    """Generates summaries of product reviews."""
    
    def __init__(self, llm_client: LLMClient, debug: bool = False):
        """
        Initialize the summarizer.
        
        Args:
            llm_client: The LLM client to use for summarization
            debug: Whether to print debug information
        """
        self.llm_client = llm_client
        self.debug = debug
        self.searcher = ReviewSearcher()
    
    async def search_reviews_for_models(self, listings: list[Listing]) -> dict[str, list[dict]]:
        """
        Search reviews for each unique product model only once.
        Returns a dict mapping normalized_model → list of review dicts.
        Deduplicates models to avoid redundant searches.
        
        Args:
            listings: List of listings to get unique models from
            
        Returns:
            Dictionary mapping normalized model names to review lists
        """
        # Get unique models using normalized names for de-duplication
        # Keep track of both original and normalized names
        seen_normalized = set()
        unique_models = []  # List of (original_model, normalized_model) tuples
        
        for listing in listings:
            if listing.product_model:
                normalized = normalize_model_name(listing.product_model)
                if normalized and normalized not in seen_normalized:
                    unique_models.append((listing.product_model, normalized))
                    seen_normalized.add(normalized)
        
        if not unique_models:
            return {}
        
        # Extract just the original model names for display
        original_models = [m[0] for m in unique_models]
        console.print(f"  [dim]Searching reviews for {len(unique_models)} unique model(s): {', '.join(original_models)}[/dim]")
        
        # Search for each model concurrently using the original name (for better search results)
        results = await asyncio.gather(*[self.searcher.search_reviews(model[0]) for model in unique_models])
        
        # Map normalized_model → reviews (using normalized key for deduplication)
        reviews_cache = {}
        for (original, normalized), reviews in zip(unique_models, results):
            reviews_cache[normalized] = reviews
        
        if self.debug:
            for (original, normalized), reviews in zip(unique_models, results):
                console.print(f"  [dim]  → {original} ({normalized}): {len(reviews)} review(s)[/dim]")
        
        return reviews_cache

    async def generate_summary_for_model(self, model: str, raw_reviews: list[dict]) -> dict[str, Any]:
        """
        Generate a summary for a specific model's reviews.
        
        Args:
            model: The product model name
            raw_reviews: List of review dictionaries
            
        Returns:
            Dictionary with summary and links
        """
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
            raw    = await self.llm_client.chat(prompt, temperature=0.2)
            parsed = extract_json(raw)
            if isinstance(parsed, dict):
                summary = parsed.get("summary", "Summary unavailable.")
            else:
                summary = "Summary unavailable."
        except Exception as e:
            summary = f"Error generating summary: {e}"
        
        return {"summary": summary, "links": review_links}

    async def aggregate_reviews(self, listings: list[Listing]) -> None:
        """
        Search reviews per unique model, generate summaries, then assign to listings.
        Uses normalized model names for de-duplication.
        
        Args:
            listings: List of listings to aggregate reviews for
        """
        console.print("[bold cyan]Step 4: Aggregating reviews...[/bold cyan]")
        
        # Search for reviews once per unique model (using normalized names for de-duplication)
        reviews_cache = await self.search_reviews_for_models(listings)
        
        # Generate summaries once per unique normalized model
        summary_cache = {}
        
        # Get all unique normalized models from listings
        normalized_models = set()
        for listing in listings:
            if listing.product_model:
                normalized = normalize_model_name(listing.product_model)
                if normalized:
                    normalized_models.add(normalized)
        
        for normalized_model in normalized_models:
            # Find the original model name to use for the summary
            # Use the first listing's original model name
            original_model = None
            for listing in listings:
                if listing.product_model and normalize_model_name(listing.product_model) == normalized_model:
                    original_model = listing.product_model
                    break
            
            if original_model:
                summary_cache[normalized_model] = await self.generate_summary_for_model(
                    original_model, 
                    reviews_cache.get(normalized_model, [])
                )
        
        # Assign cached summaries to all listings with that model (using normalized lookup)
        for listing in listings:
            if listing.product_model:
                normalized = normalize_model_name(listing.product_model)
                if normalized and normalized in summary_cache:
                    summary_data = summary_cache[normalized]
                    listing.review_summary = summary_data["summary"]
                    listing.review_links = summary_data["links"]
        
        console.print(f"  Done for {len(listings)} listings ({len(unique_models)} unique model(s))\n")
