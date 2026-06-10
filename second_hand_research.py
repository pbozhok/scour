"""
Scour — All the listings. None of the junk.
Platforms : DBA, Vinted, Tradera
LLM       : Google Gemini (gemini-2.0-flash-latest) OR Mistral AI (mistral-large-latest)
Reviews   : DuckDuckGo HTML scrape (free, no key needed)
            OR SerpAPI (set SERPAPI_KEY env var for better results)

Environment variables:
  GOOGLE_API_KEY or GEMINI_API_KEY  — your Google Gemini API key (for --llm=gemini)
  MISTRAL_API_KEY                   — your Mistral API key (for --llm=mistral)
  SERPAPI_KEY                       — optional, leave empty to use free DuckDuckGo fallback

Usage:
  python second_hand_research.py "query" --debug
  python second_hand_research.py "query" --llm mistral --debug
  python second_hand_research.py "query" --no-filter --no-score --no-reviews
"""

import asyncio
import argparse

from rich.console import Console

import config
# Import module directories to trigger scraper/filter/processor/reviewer registration
import scrapers
import processors
import filters
import reviewers
import rankers
from core.logging import get_logger
from core.pipeline import Pipeline, PipelineConfig
from core.injection import register_llm_providers
from output import display_results_from_context

register_llm_providers()

parser = argparse.ArgumentParser(description="Second-hand product research agent")
parser.add_argument("query", type=str, help="The search query for second-hand listings")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
parser.add_argument("--no-reviews", action="store_true", help="Skip review extraction and summarization")
parser.add_argument("--no-filter", action="store_true", help="Skip LLM-based filtering")
parser.add_argument("--no-score", action="store_true", help="Skip LLM-based scoring")
parser.add_argument("--llm", type=str, default="gemini", choices=["gemini", "mistral"], help="LLM backend (default: gemini)")
parser.add_argument("--currency", type=str, default="EUR", choices=["EUR", "DKK", "SEK"], help="Target currency (default: EUR)")
parser.add_argument("--no-preprocess", action="store_true", help="Skip query pre-processing")
parser.add_argument("--max-keywords", type=int, default=config.DEFAULT_MAX_KEYWORDS, help=f"Max search keywords (default: {config.DEFAULT_MAX_KEYWORDS})")

logger = get_logger(__name__, module_name="second_hand_research")
console = Console()


def main():
    args = parser.parse_args()

    if args.debug:
        console.print("[yellow]Debug mode enabled[/yellow]")

    pipeline_config = PipelineConfig(
        query=args.query,
        max_results=config.DEFAULT_MAX_RESULTS,
        max_keywords=args.max_keywords,
        target_currency=args.currency,
        llm_backend=args.llm,
        skip_preprocess=args.no_preprocess,
        skip_filter=args.no_filter,
        skip_score=args.no_score,
        skip_reviews=args.no_reviews,
        debug=args.debug,
    )

    pipeline = Pipeline()
    context = asyncio.run(pipeline.execute(pipeline_config))
    display_results_from_context(context, args.query, skip_reviews=args.no_reviews)


if __name__ == "__main__":
    main()
