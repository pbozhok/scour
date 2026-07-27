"""
Data models for listings and related entities.
"""

from dataclasses import dataclass, field


@dataclass
class Listing:
    """Represents a second-hand product listing from a platform."""
    
    title: str
    price: float
    currency: str
    url: str
    description: str
    platform: str
    images: list[str] = field(default_factory=list)

    # Populated in later stages
    relevant: bool = False
    relevance_reason: str = ""
    product_model: str = ""
    review_summary: str = ""
    review_links: list[str] = field(default_factory=list)
    score: float = 0.0
    score_reason: str = ""
    date_posted: str = ""
    location: str = ""
