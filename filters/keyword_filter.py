"""
Keyword filter - simple keyword-based filtering for listings.

Implements BaseFilter for the modular pipeline.
"""

from typing import List, Dict, Any
from rich.console import Console

from models import Listing
from core.module import ModuleType
from core.logging import get_logger
from filters.base import BaseFilter

console = Console()
logger = get_logger(__name__, module_name="filters.keyword_filter")


class KeywordFilter(BaseFilter):
    """Simple keyword-based filtering for relevance checking."""
    
    name = "keyword-filter"
    module_type = ModuleType.FILTER
    version = "1.0.0"
    
    def __init__(self, debug: bool = False):
        super().__init__()
        self.debug = debug
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization succeeded
        """
        self._initialized = True
        self.debug = config.get("debug", False)
        logger.info("KeywordFilter initialized")
        return True
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized
    
    async def filter(self, listings: List[Any], query: str, context: Dict[str, Any]) -> List[Any]:
        """
        Simple keyword-based filtering.
        Keeps listings that contain query keywords in title or description.
        
        Args:
            listings: List of listings to filter
            query: The user's search query
            context: Additional context
            
        Returns:
            Filtered list of relevant listings
        """
        keywords = query.lower().split()
        relevant_listings = []
        discarded_count = 0
        
        for listing in listings:
            text = (getattr(listing, 'title', '') + " " + getattr(listing, 'description', '')).lower()
            # Count keyword matches
            matches = sum(1 for kw in keywords if kw in text)
            
            if matches >= max(1, len(keywords) // 2):  # At least half the keywords
                listing.relevant = True
                listing.relevance_reason = f"Contains {matches}/{len(keywords)} search keywords"
                relevant_listings.append(listing)
            else:
                listing.relevant = False
                listing.relevance_reason = f"Only {matches}/{len(keywords)} keywords"
                console.print(f"  [red]✗ {getattr(listing, 'title', 'Unknown')}: {listing.relevance_reason}[/red]")
                discarded_count += 1
        
        if discarded_count > 0:
            console.print(f"[bold yellow]{discarded_count} listings discarded[/bold yellow]")
        logger.info("Keyword filtering complete", 
                   extra={"kept": len(relevant_listings), "discarded": discarded_count})
        
        if not relevant_listings:
            console.print("[yellow]No keyword matches found. Including all listings.[/yellow]\n")
            for listing in listings:
                listing.relevant = True
                listing.relevance_reason = "Fallback: included due to no keyword matches"
            return listings
        
        return relevant_listings
