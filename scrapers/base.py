"""
Base scraper class with common functionality for all platform scrapers.

All scrapers must inherit from this class which implements the Module interface.
"""

from abc import abstractmethod
from typing import Optional, List, Dict, Any

from rich.console import Console

from core.module import Module, ModuleType, PipelineContext
from models import Listing
from utils import parse_price
import config

console = Console()


class BaseScraper(Module):
    """
    Base class for platform-specific scrapers.
    
    Inherits from Module and implements the scraper-specific interface.
    All platform scrapers (DBA, Vinted, Tradera, etc.) must inherit from this class.
    """
    
    name: str = "base-scraper"
    module_type: ModuleType = ModuleType.SCRAPER
    version: str = "1.0.0"
    platform: str = "Unknown"
    
    def __init__(self, headers: Optional[dict] = None, debug: bool = False):
        """
        Initialize the scraper.
        
        Args:
            headers: HTTP headers to use for requests
            debug: Whether to print debug information
        """
        self.headers = headers or config.HEADERS
        self.debug = debug
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
        if self.debug:
            console.print(f"[blue]Initialized {self.name} scraper[/blue]")
        return True
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized and bool(self.platform) and self.platform != "Unknown"
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        self._initialized = False
        if self.debug:
            console.print(f"[blue]Cleaned up {self.name} scraper[/blue]")
    
    @abstractmethod
    async def scrape(self, query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> List[Listing]:
        """
        Scrape listings for the given query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Listing objects
        """
        pass
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the scraper module.
        
        This is the main entry point called by the pipeline.
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified context with listings added
        """
        if not self._initialized:
            self.initialize(context.config)
        
        try:
            # Check if there are multiple search queries in metadata
            search_queries = context.get_metadata("search_queries")
            if search_queries and isinstance(search_queries, list):
                # Use all search queries
                all_listings = []
                for query in search_queries:
                    listings = await self.scrape(
                        query,
                        context.config.get("max_results", config.DEFAULT_MAX_RESULTS)
                    )
                    all_listings.extend(listings)
                context.add_listings(all_listings)
                context.set_metadata(f"{self.name}_count", len(all_listings))
            else:
                # Fallback to single query from context
                listings = await self.scrape(
                    context.query, 
                    context.config.get("max_results", config.DEFAULT_MAX_RESULTS)
                )
                context.add_listings(listings)
                context.set_metadata(f"{self.name}_count", len(listings))
            
        except Exception as e:
            context.add_error(
                module_name=self.name,
                error_type="SCRAPE_ERROR",
                message=str(e),
                context={"platform": self.platform, "query": context.query}
            )
        
        return context
    
    def log_debug(self, message: str):
        """Print debug message if debug mode is enabled."""
        if self.debug:
            console.print(message)
    
    @staticmethod
    def parse_price(text: str) -> float:
        """Parse price from text (delegates to utils)."""
        return parse_price(text)
