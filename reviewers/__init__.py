"""
Reviewers module - review search and summarization.

Available reviewers:
- ReviewSearcher: Searches for product reviews (DuckDuckGo, SerpAPI)
- ReviewAggregator: Module that aggregates reviews for listings (REVIEWER type)

Usage:
    from reviewers import ReviewSearcher, ReviewAggregator
"""

from .search import ReviewSearcher
from .review_aggregator import ReviewAggregator

# Auto-register reviewers with the global registry
from core.registry import registry

try:
    registry.register(ReviewAggregator())
except:
    pass

__all__ = ["ReviewSearcher", "ReviewAggregator"]
