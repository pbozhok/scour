"""
FastAPI application for Second-Hand Search Web Interface

This module provides the main FastAPI application that serves:
1. REST API endpoints for search functionality
2. Static files for the frontend
3. HTML templates for the web interface

The application reuses existing core modules (scrapers, filters, processors, rankers)
through the Pipeline and adapters.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from web.backend.models.schemas import ErrorResponse

# Import API routers
from web.backend.api import search, search_sse


# Configuration - use absolute paths
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
STATIC_DIR_STR = str(BASE_DIR / "web" / "frontend" / "static")
TEMPLATES_DIR_STR = str(BASE_DIR / "web" / "frontend" / "templates")
INDEX_HTML_PATH = str(BASE_DIR / "web" / "frontend" / "templates" / "index.html")

# Check if files exist
if not os.path.exists(STATIC_DIR_STR):
    raise RuntimeError(f"Static directory not found: {STATIC_DIR_STR}")
if not os.path.exists(INDEX_HTML_PATH):
    raise RuntimeError(f"Index.html not found: {INDEX_HTML_PATH}")


# Create FastAPI application
app = FastAPI(
    title="Second-Hand Search API",
    description="Web interface for second-hand product search tool",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# CORS Middleware (configurable for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"^.*\.localhost$",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR_STR), name="static")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions and return standardized error response."""
    # Log the error
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    # Return standardized error response
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred. Please try again later.",
            details={"type": type(exc).__name__, "strerror": str(exc)}
        ).dict(exclude_none=True),
    )


# Include API routers
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(search_sse.router, prefix="/api/v1", tags=["search", "sse"])


# Root endpoint - serve the main HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main web interface page."""
    # Read the HTML file directly to avoid Jinja2 caching issues
    try:
        with open(INDEX_HTML_PATH, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Index.html not found")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "version": "1.0.0"}


# For development: allow running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
