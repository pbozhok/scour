"""
Deduplicator - removes duplicate listings based on URL.

Implements BaseProcessor for the modular pipeline.
"""

from typing import List, Dict, Any
from rich.console import Console

from models import Listing
from core.module import ModuleType
from core.logging import get_logger
from processors.base import BaseProcessor

console = Console()
logger = get_logger(__name__, module_name="processors.deduplicator")


class Deduplicator(BaseProcessor):
    """Removes duplicate listings based on URL."""
    
    name = "deduplicator"
    module_type = ModuleType.PROCESSOR
    version = "1.0.0"
    
    def __init__(self, debug: bool = False):
        """
        Initialize the deduplicator.
        
        Args:
            debug: Whether to print debug information
        """
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
        logger.info("Deduplicator initialized")
        return True
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized
    
    async def process(self, listings: List[Any], context: Dict[str, Any]) -> List[Any]:
        """
        Remove duplicate listings based on URL.
        
        Args:
            listings: List of listings potentially containing duplicates
            context: Additional context
            
        Returns:
            List of unique listings
        """
        if not listings:
            return listings
        
        seen_urls = set()
        unique_listings = []
        duplicates_removed = 0
        
        for listing in listings:
            url = getattr(listing, 'url', None)
            if url and url in seen_urls:
                duplicates_removed += 1
            else:
                if url:
                    seen_urls.add(url)
                unique_listings.append(listing)
        
        if duplicates_removed > 0:
            logger.info("Deduplication complete", 
                       extra={"duplicates_removed": duplicates_removed, 
                              "unique_remaining": len(unique_listings)})
            if self.debug:
                console.print(f"  [dim]Removed {duplicates_removed} duplicate listing(s)[/dim]")
        
        return unique_listings
