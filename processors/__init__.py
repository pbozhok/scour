"""
Processors module - pipeline stage implementations.

This module provides data processing functionality for the second-hand research agent.
All processors inherit from BaseProcessor which implements the Module interface.

Available processors:
- PriceConverter: Converts listing prices between currencies (EUR, DKK, SEK)
- ModelExtractor: Extracts product model names from listing titles using LLM
- DescriptionFetcher: Fetches full descriptions from product pages
- Deduplicator: Removes duplicate listings based on URL
- QueryPreprocessor: Pre-processes and expands search queries

Available preprocessor modules:
- QueryPreprocessorModule: Module version of query preprocessor (PREPROCESSOR type)

Usage:
    from processors import PriceConverter, ModelExtractor, DescriptionFetcher
    
    processor = PriceConverter(debug=True)
    processed_listings = await processor.process(listings, config)
"""

from .base import BaseProcessor
from .price_converter import PriceConverter
from .model_extractor import ModelExtractor
from .description_fetcher import DescriptionFetcher
from .deduplicator import Deduplicator
from .query_preprocessor import QueryPreprocessor, preprocess_query
from .query_preprocessor_module import QueryPreprocessorModule

# Auto-register processors with the global registry
from core.registry import registry

# Create instances and register (only those that inherit from BaseProcessor)
try:
    if issubclass(PriceConverter, BaseProcessor):
        registry.register(PriceConverter(debug=False))
except:
    pass

try:
    if issubclass(ModelExtractor, BaseProcessor):
        registry.register(ModelExtractor())
except:
    pass

try:
    if issubclass(DescriptionFetcher, BaseProcessor):
        registry.register(DescriptionFetcher())
except:
    pass

try:
    if issubclass(Deduplicator, BaseProcessor):
        registry.register(Deduplicator())
except:
    pass

# Register the query preprocessor module (PREPROCESSOR type)
try:
    registry.register(QueryPreprocessorModule())
except:
    pass

__all__ = [
    "BaseProcessor",
    "PriceConverter", 
    "ModelExtractor", 
    "DescriptionFetcher",
    "Deduplicator",
    "QueryPreprocessor", 
    "QueryPreprocessorModule",
    "preprocess_query"
]
