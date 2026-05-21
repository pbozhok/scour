"""
Base filter class with common functionality for all filters.

All filters must inherit from this class which implements the Module interface.
"""

from abc import abstractmethod
from typing import List, Dict, Any

from core.module import Module, ModuleType, PipelineContext


class BaseFilter(Module):
    """
    Base class for all filters.
    
    Inherits from Module and implements the filter-specific interface.
    All filters (keyword, LLM-based) must inherit from this class.
    """
    
    name: str = "base-filter"
    module_type: ModuleType = ModuleType.FILTER
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
    async def filter(self, listings: List[Any], query: str, context: Dict[str, Any]) -> List[Any]:
        """
        Filter listings based on criteria.
        
        Args:
            listings: List of listings to filter
            query: The search query
            context: Additional context for filtering
            
        Returns:
            Filtered list of listings
        """
        pass
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the filter module.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with filtered listings
        """
        if not self._initialized:
            self.initialize(context.config)
        
        try:
            listings = context.get_listings()
            
            # Use cleaned query from metadata if available, otherwise use context.query
            query = context.get_metadata("cleaned_query", default=context.query)
            
            filtered = await self.filter(listings, query, context.config)
            # Clear and add filtered listings
            context.listings = filtered
            context.set_metadata(f"{self.name}_filtered", len(filtered))
            context.set_metadata(f"{self.name}_removed", len(listings) - len(filtered))
            
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="FILTER_ERROR",
                message=str(e),
                context={"original_count": len(listings), "query": context.query}
            )
        
        return context
