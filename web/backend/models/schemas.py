"""
Pydantic models for the Scour API.

These models define the request/response schemas for the web interface API.
They are used for:
1. Request validation
2. Response serialization
3. OpenAPI/Swagger documentation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string",
        json_schema_extra={"example": "leather jacket"}
    )
    max_results: Optional[int] = Field(
        default=40,
        ge=1,
        le=100,
        description="Maximum number of results to return",
        json_schema_extra={"example": 40}
    )
    currency: Optional[str] = Field(
        default="EUR",
        description="Target currency for price conversion",
        json_schema_extra={"example": "EUR"}
    )
    use_filter: Optional[bool] = Field(
        default=True,
        description="Enable LLM-based filtering",
        json_schema_extra={"example": True}
    )
    use_reviews: Optional[bool] = Field(
        default=True,
        description="Enable review extraction",
        json_schema_extra={"example": True}
    )
    use_scoring: Optional[bool] = Field(
        default=True,
        description="Enable LLM-based scoring",
        json_schema_extra={"example": True}
    )
    sort_by: Optional[str] = Field(
        default="score",
        description="Sort results by: score, price_asc, price_desc, date",
        json_schema_extra={"example": "score"}
    )


class ItemResponse(BaseModel):
    """Response model for a single search result item."""

    id: str = Field(
        ...,
        description="Unique item identifier",
        json_schema_extra={"example": "dba-12345"}
    )
    title: str = Field(
        ...,
        description="Item title",
        json_schema_extra={"example": "Vintage Leather Jacket"}
    )
    price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Item price",
        json_schema_extra={"example": 99.99}
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code (EUR, DKK, SEK)",
        json_schema_extra={"example": "EUR"}
    )
    posted_date: Optional[str] = Field(
        default=None,
        description="Date posted (YYYY-MM-DD)",
        json_schema_extra={"example": "2025-05-20"}
    )
    original_url: str = Field(
        ...,
        description="URL to original advertisement",
        json_schema_extra={"example": "https://dba.dk/item/12345"}
    )
    image_url: Optional[str] = Field(
        default=None,
        description="URL to item image",
        json_schema_extra={"example": "https://dba.dk/images/12345.jpg"}
    )
    platform: str = Field(
        ...,
        description="Source platform (DBA, Vinted, Tradera)",
        json_schema_extra={"example": "DBA"}
    )
    score: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Relevance score (higher is better)",
        json_schema_extra={"example": 9.5}
    )
    score_reason: Optional[str] = Field(
        default=None,
        description="Reason for the score",
        json_schema_extra={"example": "High relevance: matches all keywords and has good reviews"}
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Item description (truncated)",
        json_schema_extra={"example": "Vintage leather jacket in excellent condition"}
    )
    location: Optional[str] = Field(
        default=None,
        description="Item location",
        json_schema_extra={"example": "Copenhagen"}
    )


class ReviewResponse(BaseModel):
    """Response model for review information."""

    item_id: str = Field(
        ...,
        description="Reference to item",
        json_schema_extra={"example": "dba-12345"}
    )
    average_rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Average rating (1.0 to 5.0)",
        json_schema_extra={"example": 4.5}
    )
    review_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of reviews",
        json_schema_extra={"example": 12}
    )
    summary: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Summarized review text",
        json_schema_extra={"example": "Great condition, fast shipping"}
    )
    sentiment: Optional[str] = Field(
        default=None,
        description="Overall sentiment (positive, neutral, negative)",
        json_schema_extra={"example": "positive"}
    )
    source: Optional[str] = Field(
        default=None,
        description="Review source",
        json_schema_extra={"example": "DuckDuckGo"}
    )


class ToggleStates(BaseModel):
    """Model for toggle states."""

    filtering: bool = Field(
        default=True,
        description="Filtering enabled"
    )
    reviewing: bool = Field(
        default=True,
        description="Reviewing enabled"
    )
    scoring: bool = Field(
        default=True,
        description="Scoring enabled"
    )


class SearchResponse(BaseModel):
    """Complete response model for search endpoint."""

    query: str = Field(
        ...,
        description="Original search query",
        json_schema_extra={"example": "leather jacket"}
    )
    results: List[ItemResponse] = Field(
        default_factory=list,
        description="List of matching items"
    )
    reviews: Dict[str, ReviewResponse] = Field(
        default_factory=dict,
        description="Reviews keyed by item_id"
    )
    total_results: int = Field(
        default=0,
        ge=0,
        description="Total number of results",
        json_schema_extra={"example": 25}
    )
    llm_filtered: int = Field(
        default=0,
        ge=0,
        description="Number of items filtered out by LLM filtering",
        json_schema_extra={"example": 5}
    )
    sort_by: str = Field(
        default="score",
        description="Current sort order"
    )
    toggles: ToggleStates = Field(
        default_factory=ToggleStates,
        description="Current toggle states"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp"
    )
    search_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this search (used for SSE phase tracking)",
        json_schema_extra={"example": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"}
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(
        ...,
        description="Error type",
        json_schema_extra={"example": "invalid_request"}
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        json_schema_extra={"example": "Please enter a valid search query"}
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details",
        json_schema_extra={"example": {"field": "query", "issue": "too short"}}
    )
