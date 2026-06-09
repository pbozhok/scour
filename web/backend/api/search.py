"""
Search API endpoints for the web interface.

This module provides the main search endpoint that:
1. Accepts search requests from the frontend
2. Orchestrates the existing Pipeline to execute the search
3. Converts results to API format using adapters
4. Returns structured JSON responses
"""

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from web.backend.models.schemas import (
    ErrorResponse,
    SearchRequest,
    SearchResponse,
)
from web.shared.adapters import create_search_response, search_request_to_pipeline_config

# Import existing core modules
from core.pipeline import Pipeline, PipelineConfig
from core.registry import registry

# Import SearchProgressTracker for phase updates
from web.backend.api.search_sse import SearchProgressTracker, active_searches, get_search_tracker

# Import module packages to trigger auto-registration with registry
import scrapers
import processors
import filters
import reviewers
import rankers

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_pipeline() -> Pipeline:
    """Dependency that provides a Pipeline instance."""
    # Create a new pipeline for each request to avoid state issues
    # In production, consider using a pool or singleton
    return Pipeline()


@router.get("/search", response_model=SearchResponse, responses={
    400: {"model": ErrorResponse, "description": "Invalid request"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
    504: {"model": ErrorResponse, "description": "Search timeout"},
})
async def search_items(
    request: Request,
    query: str = Query(..., min_length=1, max_length=500, description="Search query string"),
    max_results: Optional[int] = Query(default=40, ge=1, le=100, description="Maximum results"),
    currency: Optional[str] = Query(default="EUR", description="Target currency"),
    use_filter: Optional[bool] = Query(default=True, description="Enable filtering"),
    use_reviews: Optional[bool] = Query(default=True, description="Enable reviews"),
    use_scoring: Optional[bool] = Query(default=True, description="Enable scoring"),
    sort_by: Optional[str] = Query(default="score", description="Sort by: score, price_asc, price_desc, date"),
    search_id: Optional[str] = Query(default=None, description="Optional search ID for SSE tracking"),
    pipeline: Pipeline = Depends(get_pipeline),
) -> SearchResponse:
    """
    Search for second-hand items.
    
    This endpoint:
    1. Validates the search request
    2. Executes the search using the existing Pipeline
    3. Converts results to API format
    4. Returns structured response with item cards data
    
    **Note**: This endpoint runs the same search logic as the CLI,
    just formatted for web display.
    """
    # Use provided search_id or generate a new one
    # Use get_search_tracker to ensure we reuse existing tracker (if SSE connected early)
    if search_id:
        tracker = await get_search_tracker(search_id)
    else:
        search_id = str(uuid.uuid4())
        tracker = await get_search_tracker(search_id)
    
    # Build the search request model
    search_request = SearchRequest(
        query=query,
        max_results=max_results,
        currency=currency,
        use_filter=use_filter,
        use_reviews=use_reviews,
        use_scoring=use_scoring,
        sort_by=sort_by,
    )
    
    # Convert to pipeline config
    pipeline_config_dict = search_request_to_pipeline_config(search_request)
    
    try:
        # Build PipelineConfig from the request
        pipeline_config = PipelineConfig(
            query=query,
            max_results=max_results or 40,
            target_currency=currency or "EUR",
            llm_backend="mistral",  # Default, can be made configurable
            skip_preprocess=False,
            skip_filter=not use_filter,
            skip_score=not use_scoring,
            skip_reviews=not use_reviews,
            debug=False
        )
        
        # Load modules into pipeline
        pipeline.load_modules()
        
        # Build a lookup so each phase_callback call is O(1)
        _phase_index = {p['id']: i for i, p in enumerate(SearchProgressTracker.PHASES)}
        _n_phases = len(SearchProgressTracker.PHASES)

        def phase_callback(phase_name: str, current: int, total: int):
            idx = _phase_index.get(phase_name)
            if idx is not None:
                tracker.current_phase_index = idx
                tracker.progress = int((idx + 1) / _n_phases * 100)
        
        # Execute the pipeline with phase callback
        try:
            logger.info(f"Starting pipeline execution for search: {search_id}")
            context = await pipeline.execute(pipeline_config, phase_callback=phase_callback)
            logger.info(f"Pipeline completed successfully for search: {search_id}")
        except Exception as e:
            logger.exception(f"Pipeline execution failed for search {search_id}: {e}")
            tracker.set_error(str(e))
            raise
        listings = context.listings
        
        # Mark complete
        tracker.complete()
        
        # Get llm_filtered count from metadata
        # BaseFilter.execute() sets {module_name}_removed, where module_name is "llm-filter" or "keyword-filter"
        llm_filtered = 0
        if context.metadata:
            llm_filtered = context.metadata.get('llm-filter_removed', 0) or context.metadata.get('keyword-filter_removed', 0)
        
        # Create response data with search_id
        response = create_search_response(
            query=query,
            listings=listings or [],
            reviews={},
            request=search_request,
            total_results=len(listings) if listings else 0,
            llm_filtered=llm_filtered
        )
        
        # Set search_id on the response model
        response.search_id = search_id
        
        logger.info(f"Search completed: {query} -> {len(listings)} results ({llm_filtered} items filtered by LLM)")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error for query '{query}': {e}")
        tracker.set_error(str(e))
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="validation_error",
                message=str(e),
                details={"query": query}
            ).dict()
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for query '{query}': {e}")
        tracker.set_error("Search is taking longer than usual. Please try again.")
        raise HTTPException(
            status_code=504,
            detail=ErrorResponse(
                error="timeout",
                message="Search is taking longer than usual. Please try again.",
                details={"query": query, "timeout_seconds": str(e.args[0]) if e.args else None}
            ).dict()
        )
    except Exception as e:
        logger.exception(f"Unexpected error for query '{query}': {e}")
        tracker.set_error(str(e))
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred. Please try again later.",
                details={"type": type(e).__name__, "message": str(e)}
            ).dict()
        )


@router.get("/search/quick", response_model=SearchResponse)
async def quick_search(
    query: str = Query(..., min_length=1, max_length=500, description="Search query string"),
    pipeline: Pipeline = Depends(get_pipeline),
) -> SearchResponse:
    """
    Quick search with all default options.
    
    This is a simplified endpoint that uses all default values for:
    - max_results: 40
    - currency: EUR
    - use_filter: true
    - use_reviews: true
    - use_scoring: true
    - sort_by: score
    """
    search_request = SearchRequest(query=query)
    
    try:
        # Build PipelineConfig
        pipeline_config = PipelineConfig(
            query=query,
            max_results=40,
            target_currency="EUR",
            llm_backend="mistral",
            skip_preprocess=False,
            skip_filter=False,
            skip_score=False,
            skip_reviews=False,
            debug=False
        )
        
        # Load modules and execute
        pipeline.load_modules()
        context = await pipeline.execute(pipeline_config)
        listings = context.listings
        
        return create_search_response(
            query=query,
            listings=listings or [],
            reviews={},
            request=search_request,
            total_results=len(listings) if listings else 0
        )
    except Exception as e:
        logger.exception(f"Error in quick search for '{query}': {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="search_error",
                message=f"Search failed: {str(e)}",
                details={"query": query}
            ).dict()
        )
