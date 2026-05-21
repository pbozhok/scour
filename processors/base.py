"""
Base processor class with common functionality for all processors.

All processors must inherit from this class which implements the Module interface.
"""

from abc import abstractmethod
from typing import List, Dict, Any

from core.module import Module, ModuleType, PipelineContext


class BaseProcessor(Module):
    """
    Base class for all processors.
    
    Inherits from Module and implements the processor-specific interface.
    All processors (description_fetcher, price_converter, model_extractor) must inherit from this class.
    """
    
    name: str = "base-processor"
    module_type: ModuleType = ModuleType.PROCESSOR
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
    async def process(self, listings: List[Any], context: Dict[str, Any]) -> List[Any]:
        """
        Process listings (transform/augment data).
        
        Args:
            listings: List of listings to process
            context: Additional context for processing
            
        Returns:
            Processed list of listings
        """
        pass
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the processor module.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with processed listings
        """
        if not self._initialized:
            self.initialize(context.config)
        
        try:
            listings = context.get_listings()
            processed = await self.process(listings, context.config)
            context.listings = processed
            context.set_metadata(f"{self.name}_processed", len(processed))
            
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="PROCESSOR_ERROR",
                message=str(e),
                context={"original_count": len(listings), "query": context.query}
            )
        
        return context
