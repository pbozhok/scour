"""
Base reviewer class with common functionality for all reviewers.

All reviewers must inherit from this class which implements the Module interface.
"""

from abc import abstractmethod
from typing import List, Dict, Any

from core.module import Module, ModuleType, PipelineContext


class BaseReviewer(Module):
    """
    Base class for all reviewers.
    
    Inherits from Module and implements the reviewer-specific interface.
    All reviewers (search, summarizer) must inherit from this class.
    """
    
    name: str = "base-reviewer"
    module_type: ModuleType = ModuleType.REVIEWER
    version: str = "1.0.0"
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the module with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization succeeded
        """
        self._initialized = True
        return True
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        self._initialized = False
    
    @abstractmethod
    async def review(self, listings: List[Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch and summarize reviews for listings.
        
        Args:
            listings: List of listings to review
            context: Additional context for reviewing
            
        Returns:
            Dictionary with review summaries keyed by listing ID
        """
        pass
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the reviewer module.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with review summaries added to listing metadata
        """
        if not self._initialized:
            self.initialize(context.config)
        
        try:
            listings = context.get_listings()
            reviews = await self.review(listings, context.config)
            
            # Add review summaries to listing metadata
            for listing in listings:
                if listing.id in reviews:
                    if not hasattr(listing, 'metadata'):
                        listing.metadata = {}
                    listing.metadata['reviews'] = reviews[listing.id]
            
            context.set_metadata(f"{self.name}_reviewed", len(reviews))
            
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="REVIEW_ERROR",
                message=str(e),
                context={"listing_count": len(listings), "query": context.query}
            )
        
        return context
