"""
Filters module - relevance filtering implementations.

This module provides filtering functionality for the second-hand research agent.
All filters inherit from BaseFilter which implements the Module interface.

Available filters:
- KeywordFilter: Simple keyword-based filtering (no LLM required)
- LLMFilter: AI-powered relevance filtering using LLM

Usage:
    from filters import KeywordFilter, LLMFilter
    
    filter = KeywordFilter()
    filtered_listings = await filter.filter(listings, query, config)
"""

from .base import BaseFilter
from .keyword_filter import KeywordFilter
from .llm_filter import LLMFilter

# Auto-register filters with the global registry
from core.registry import registry

try:
    if issubclass(KeywordFilter, BaseFilter):
        registry.register(KeywordFilter(debug=False))
except Exception:
    pass

try:
    if issubclass(LLMFilter, BaseFilter):
        registry.register(LLMFilter())
except Exception:
    pass

__all__ = ["BaseFilter", "KeywordFilter", "LLMFilter"]
