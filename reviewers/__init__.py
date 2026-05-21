"""
Reviewers module - review search and summarization.

This module provides review aggregation functionality for the second-hand research agent.
All reviewers inherit from BaseReviewer which implements the Module interface.

Available reviewers:
- ReviewSearcher: Searches for product reviews from various sources (DuckDuckGo, SerpAPI)
- ReviewSummarizer: Summarizes reviews using LLM
- ReviewAggregator: Module that aggregates reviews for listings (REVIEWER type)

Usage:
    from reviewers import ReviewSearcher, ReviewSummarizer, ReviewAggregator
    
    searcher = ReviewSearcher()
    reviews = await searcher.search_duckduckgo("iPhone 15", max_results=3)
"""

from .base import BaseReviewer
from .search import ReviewSearcher
from .summarizer import ReviewSummarizer
from .review_aggregator import ReviewAggregator

# Auto-register reviewers with the global registry
from core.registry import registry

# Register the review aggregator module
try:
    registry.register(ReviewAggregator())
except:
    pass

__all__ = ["BaseReviewer", "ReviewSearcher", "ReviewSummarizer", "ReviewAggregator"]
