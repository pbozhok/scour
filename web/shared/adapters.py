"""
Adapters between core models and API models.

These adapters provide a clean separation between:
1. Core domain models (Listing, etc.) from the existing CLI
2. API models (ItemResponse, SearchResponse, etc.) for the web interface

This allows the web interface to evolve independently while keeping
the core modules unchanged.
"""

from datetime import datetime
from typing import Optional

from models import Listing

from web.backend.models.schemas import (
    ItemResponse,
    ReviewResponse,
    SearchRequest,
    SearchResponse,
    ToggleStates,
)


def listing_to_item_response(listing: Listing, index: int = 0) -> ItemResponse:
    """
    Convert a core Listing model to an API ItemResponse model.
    
    Args:
        listing: The core Listing object from scrapers/pipeline
        index: Optional index for generating unique IDs
        
    Returns:
        ItemResponse: API-compatible item representation
    """
    # Generate a unique ID for the item
    # Use the URL as base, append index if needed for deduplication
    item_id = f"{listing.platform.lower()}-{index}"
    
    # Get the first image if available
    image_url = listing.images[0] if listing.images else None
    
    # Parse date if available
    posted_date = None
    if listing.date_posted:
        try:
            # Try to parse various date formats
            if len(listing.date_posted) >= 10:
                # Assume YYYY-MM-DD format or extract date part
                posted_date = listing.date_posted[:10]
        except (ValueError, AttributeError):
            pass
    
    return ItemResponse(
        id=item_id,
        title=listing.title,
        price=listing.price,
        currency=listing.currency,
        posted_date=posted_date,
        original_url=listing.url,
        image_url=image_url,
        platform=listing.platform,
        score=listing.score,
        score_reason=listing.score_reason if listing.score_reason else None,
        description=listing.description[:500] if listing.description else None,
        location=None  # Location not currently in Listing model
    )


def review_summary_to_review_response(
    review_summary: str,
    review_links: list[str],
    item_id: str
) -> Optional[ReviewResponse]:
    """
    Convert review information from Listing to ReviewResponse.
    
    Args:
        review_summary: The summarized review text from Listing
        review_links: List of review URLs from Listing
        item_id: The item ID to reference
        
    Returns:
        ReviewResponse or None if no review data available
    """
    if not review_summary and not review_links:
        return None
    
    # Parse sentiment from review summary (simple heuristic)
    sentiment = None
    if review_summary:
        summary_lower = review_summary.lower()
        if any(word in summary_lower for word in ["excellent", "great", "perfect", "amazing", "wonderful"]):
            sentiment = "positive"
        elif any(word in summary_lower for word in ["poor", "bad", "terrible", "broken", "damaged"]):
            sentiment = "negative"
        else:
            sentiment = "neutral"
    
    # Extract rating from summary if available (e.g., "4.5/5")
    average_rating = None
    review_count = None
    if review_summary:
        import re
        # Try to find rating pattern like "4.5/5" or "4.5 out of 5"
        rating_match = re.search(r'(\d+\.?\d*)\s*/\s*(\d+)', review_summary)
        if rating_match:
            raw_rating = float(rating_match.group(1))
            scale = float(rating_match.group(2))
            if 1 <= scale <= 10 and 0 <= raw_rating <= scale:
                average_rating = round(raw_rating * 5.0 / scale, 1) if scale != 5 else raw_rating
        # Try to find count pattern like "(12 reviews)" or "from 12 users"
        count_match = re.search(r'(\d+)\s*(?:reviews?|raters?|users?)', review_summary, re.IGNORECASE)
        if count_match:
            review_count = int(count_match.group(1))
    
    return ReviewResponse(
        item_id=item_id,
        average_rating=average_rating,
        review_count=review_count,
        summary=review_summary[:1000] if review_summary else None,
        sentiment=sentiment,
        source="DuckDuckGo" if review_links else None
    )


def search_request_to_pipeline_config(
    request: SearchRequest
) -> dict:
    """
    Convert a SearchRequest to pipeline configuration.
    
    Args:
        request: The API search request
        
    Returns:
        Dictionary with pipeline configuration options
    """
    return {
        "use_filter": request.use_filter,
        "use_reviews": request.use_reviews,
        "use_scoring": request.use_scoring,
        "max_results": request.max_results,
        "currency": request.currency,
    }


def create_search_response(
    query: str,
    listings: list[Listing],
    reviews: dict[str, ReviewResponse],
    request: SearchRequest,
    total_results: int,
    llm_filtered: int = 0
) -> SearchResponse:
    """
    Create a complete SearchResponse from listings and request.
    
    Args:
        query: The original search query
        listings: List of Listing objects from pipeline
        reviews: Dictionary of ReviewResponse objects keyed by item_id
        request: The original SearchRequest
        total_results: Total number of results (may differ from len(listings) due to pagination)
        llm_filtered: Number of items filtered out by LLM filtering
        
    Returns:
        SearchResponse: Complete API response
    """
    # Convert listings to item responses
    items = [listing_to_item_response(listing, i) for i, listing in enumerate(listings)]
    
    # Create reviews dict with item IDs as keys
    reviews_dict = {}
    for i, item in enumerate(items):
        if i < len(listings):
            listing = listings[i]
            review_resp = review_summary_to_review_response(
                listing.review_summary,
                listing.review_links,
                item.id
            )
            if review_resp:
                reviews_dict[item.id] = review_resp
    
    # Handle sorting
    sort_by = request.sort_by
    if sort_by == "price_asc":
        items.sort(key=lambda x: x.price or 0)
    elif sort_by == "price_desc":
        items.sort(key=lambda x: x.price or 0, reverse=True)
    elif sort_by == "date":
        items.sort(key=lambda x: x.posted_date or "", reverse=True)
    else:  # score (default)
        items.sort(key=lambda x: x.score or 0, reverse=True)
    
    return SearchResponse(
        query=query,
        results=items,
        reviews=reviews_dict,
        total_results=total_results,
        llm_filtered=llm_filtered,
        sort_by=sort_by,
        toggles=ToggleStates(
            filtering=request.use_filter,
            reviewing=request.use_reviews,
            scoring=request.use_scoring
        ),
        timestamp=datetime.utcnow().isoformat()
    )
