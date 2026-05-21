"""
Price converter - handles currency conversion for listings.

Implements BaseProcessor for the modular pipeline.
"""

from typing import List, Dict, Any
from rich.console import Console

from models import Listing
from core.module import ModuleType
from core.logging import get_logger
from processors.base import BaseProcessor
import config

console = Console()
logger = get_logger(__name__, module_name="processors.price_converter")


class PriceConverter(BaseProcessor):
    """Handles currency conversion for listings."""
    
    name = "price-converter"
    module_type = ModuleType.PROCESSOR
    version = "1.0.0"
    
    def __init__(self, debug: bool = False):
        """
        Initialize the converter.
        
        Args:
            debug: Whether to print debug information
        """
        super().__init__()
        self.debug = debug
        self.exchange_rates = config.EXCHANGE_RATES
        self._target_currency = "EUR"  # Default, set via config
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize with configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if initialization succeeded
        """
        self._initialized = True
        self._target_currency = config.get("target_currency", "EUR")
        self.debug = config.get("debug", False)
        logger.info("PriceConverter initialized", extra={"target_currency": self._target_currency})
        return True
    
    def validate(self) -> bool:
        """
        Validate the module is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized and bool(self._target_currency)
    
    async def process(self, listings: List[Any], context: Dict[str, Any]) -> List[Any]:
        """
        Convert all listing prices to target currency.
        
        Args:
            listings: List of listings to convert
            context: Additional context (contains target_currency)
            
        Returns:
            Processed list of listings
        """
        if not listings:
            return listings
        
        target_currency = context.get("target_currency", self._target_currency)
        
        # Check if any conversion is needed
        needs_conversion = any(
            hasattr(l, 'currency') and l.currency != target_currency 
            for l in listings
        )
        
        if needs_conversion:
            logger.info("Converting prices", extra={"target_currency": target_currency, "listing_count": len(listings)})
            
            for listing in listings:
                if hasattr(listing, 'currency') and listing.currency != target_currency:
                    # Convert from listing currency to EUR first, then to target
                    source_rate = self.exchange_rates.get(listing.currency, 1.0)
                    target_rate = self.exchange_rates.get(target_currency, 1.0)
                    original_price = listing.price
                    listing.price = round(listing.price / source_rate * target_rate, 2)
                    
                    if self.debug:
                        console.print(f"  [dim]{listing.title}: {original_price} {listing.currency} → {listing.price} {target_currency}[/dim]")
                    
                    listing.currency = target_currency
        
        return listings
