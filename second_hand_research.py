"""
Second-hand product research agent
Platforms : DBA, Vinted, Tradera
LLM       : Google Gemini (gemini-2.0-flash-latest) OR Mistral AI (mistral-large-latest)
Reviews   : DuckDuckGo HTML scrape (free, no key needed)
            OR SerpAPI (set SERPAPI_KEY env var for better results)

Environment variables:
  GOOGLE_API_KEY or GEMINI_API_KEY  — your Google Gemini API key (for --llm=gemini)
  MISTRAL_API_KEY                   — your Mistral API key (for --llm=mistral)
  SERPAPI_KEY                       — optional, leave empty to use free DuckDuckGo fallback

Usage:
  # With Gemini (default)
  python second_hand_research.py "query" --debug

  # With Mistral
  python second_hand_research.py "query" --llm mistral --debug

  # Skip all LLM calls (use only scrapers and keyword filtering)
  python second_hand_research.py "query" --no-filter --no-score --no-reviews
"""

import asyncio
import random
import json
import os
import re
import urllib.parse
import argparse

import httpx
from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.table import Table

import config
from models import Listing
from utils import extract_json, parse_price, normalize_model_name
from llm import get_client
from scrapers import DBAScraper, VintedScraper, TraderaScraper

# Add argument parsing for debug flag
parser = argparse.ArgumentParser(description="Second-hand product research agent")
parser.add_argument("--debug", action="store_true", help="Enable debug logging")
parser.add_argument("--no-reviews", action="store_true", help="Skip review extraction and summarization")
parser.add_argument("--no-filter", action="store_true", help="Skip LLM-based filtering (use simple keyword matching instead)")
parser.add_argument("--no-score", action="store_true", help="Skip LLM-based scoring (sort by price instead)")
parser.add_argument("--llm", type=str, default="gemini", choices=["gemini", "mistral"], help="LLM backend to use (default: gemini)")
parser.add_argument("--currency", type=str, default="EUR", choices=["EUR", "DKK", "SEK"], help="Target currency (default: EUR)")
parser.add_argument("query", type=str, help="The search query for second-hand listings")
args = parser.parse_args()

# Initialize LLM client (will check availability)
try:
    llm_client = get_client(args.llm)
except Exception as e:
    console_startup = Console()
    console_startup.print(f"[red]Error initializing {args.llm} client: {e}[/red]")
    exit(1)

# Console and debug output
console = Console()
if args.debug:
    console.print("[yellow]Debug mode enabled[/yellow]")

# ── Wrapper for backwards compatibility ────────────────────────────────────────

async def gemini_chat(
    prompt: str,
    temperature: float = 0.0,
    max_retries: int = 5,
) -> str:
    """
    Wrapper function that calls the LLM client.
    Kept for backwards compatibility with existing code.
    """
    return await llm_client.chat(prompt, temperature, max_retries)


# ── 1. Scrapers ────────────────────────────────────────────────────────────────
#
#  Scrapers are implemented in the scrapers/ module, each in its own file:
#  - scrapers/base.py: BaseScraper abstract class
#  - scrapers/dba.py: DBAScraper for DBA.dk
#  - scrapers/vinted.py: VintedScraper for Vinted.dk
#  - scrapers/tradera.py: TraderaScraper for Tradera.com

async def log_listings(listings: list[Listing]):
    """Logs all listings if debug mode is enabled."""
    if args.debug:
        console.print("\n[yellow]Logging all listings:[/yellow]")
        for listing in listings:
            console.print(f"[blue]{listing.platform}[/blue]: {listing.title} - {listing.price} {listing.currency} ({listing.url})")


async def scrape_all(query: str, max_results: int = config.DEFAULT_MAX_RESULTS) -> list[Listing]:
    """Run all three scrapers concurrently and log listings if debug is enabled."""
    # Initialize scraper instances
    dba_scraper = DBAScraper(debug=args.debug)
    vinted_scraper = VintedScraper(debug=args.debug)
    tradera_scraper = TraderaScraper(debug=args.debug)
    
    # Run all scrapers concurrently
    results = await asyncio.gather(
        dba_scraper.scrape(query, max_results),
        vinted_scraper.scrape(query, max_results),
        tradera_scraper.scrape(query, max_results),
    )
    all_listings = [l for platform in results for l in platform]
    console.print(f"\n[bold]Total raw listings:[/bold] {len(all_listings)}\n")

    # Log all listings if debug is enabled
    await log_listings(all_listings)

    return all_listings



# ── 2. Price conversion ────────────────────────────────────────────────────────

async def convert_prices(listings: list[Listing], target_currency: str) -> None:
    """Convert all listing prices to target currency."""
    if not listings:
        return
    
    # Check if any conversion is needed
    needs_conversion = any(l.currency != target_currency for l in listings)
    if needs_conversion:
        console.print(f"[bold cyan]Converting prices to {target_currency}...[/bold cyan]")
        
        for listing in listings:
            if listing.currency != target_currency:
                # Convert from listing currency to EUR first, then to target
                source_rate = config.EXCHANGE_RATES.get(listing.currency, 1.0)
                target_rate = config.EXCHANGE_RATES.get(target_currency, 1.0)
                original_price = listing.price
                listing.price = round(listing.price / source_rate * target_rate, 2)
                
                if args.debug:
                    console.print(f"  [dim]{listing.title}: {original_price} {listing.currency} → {listing.price} {target_currency}[/dim]")
                
                listing.currency = target_currency
        
        console.print("")


# ── 3. Relevance filtering ─────────────────────────────────────────────────────

async def filter_listings_simple(listings: list[Listing], user_query: str) -> list[Listing]:
    """
    Simple keyword-based filtering fallback (when Gemini is unavailable).
    Keeps listings that contain query keywords in title or description.
    """
    keywords = user_query.lower().split()
    relevant_listings = []
    
    for listing in listings:
        text = (listing.title + " " + listing.description).lower()
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in text)
        
        if matches >= max(1, len(keywords) // 2):  # At least half the keywords
            listing.relevant = True
            listing.relevance_reason = f"Contains {matches}/{len(keywords)} search keywords"
            relevant_listings.append(listing)
    
    console.print(f"[bold green]{len(relevant_listings)} relevant listings kept (keyword-based)[/bold green]\n")
    
    if not relevant_listings:
        console.print("[yellow]No keyword matches found. Including all listings.[/yellow]\n")
        for listing in listings:
            listing.relevant = True
            listing.relevance_reason = "Fallback: included due to no keyword matches"
        return listings
    
    return relevant_listings


async def filter_listings(
    listings: list[Listing],
    user_query: str,
    batch_size: int = 20,  # Reduced batch size to lower API load
    delay_between_batches: float = 10.0,  # Increased delay to avoid rate limits
    max_retries: int = 5,
) -> list[Listing]:
    """
    Filters listings for relevance using Gemini.
    Falls back to simple keyword matching if Gemini is unavailable.
    Processes batches sequentially (not concurrently) to avoid rate limits.
    """
    
    # Use simple filter if Gemini is disabled
    if args.no_filter:
        return await filter_listings_simple(listings, user_query)

    async def judge_batch(batch: list[Listing]) -> None:
        items_json = json.dumps(
            [
                {"id": i, "title": listing.title, "description": listing.description[:400]}
                for i, listing in enumerate(batch)
            ],
            ensure_ascii=False,
        )

        prompt = f"""You are a shopping assistant. The user is looking for: "{user_query}"

Below is a JSON list of second-hand listings. For each one decide:
- relevant: true or false
- reason: one sentence explaining why

A listing is relevant if it matches the user's query closely in terms of product type, brand, or features.
Eg. if the user is looking for "iPhone 12 with good camera", a listing titled "iPhone 12 Pro Max - Excellent Camera" would be relevant, while "iPhone 12 case" would be not relevant.

Return ONLY a JSON object in this exact format:
{{"results": [{{"id": 0, "relevant": true, "reason": "..."}}]}}

Listings:
{items_json}"""

        for attempt in range(max_retries):
            try:
                raw_response = await gemini_chat(prompt)
                parsed_response = extract_json(raw_response)
                console.print(f"[blue]Parsed response:[/blue] {parsed_response}")

                if isinstance(parsed_response, dict):
                    verdicts = parsed_response.get("results", [])
                elif isinstance(parsed_response, list):
                    verdicts = parsed_response
                else:
                    verdicts = []

                for verdict in verdicts:
                    idx = verdict.get("id")
                    if idx is not None and 0 <= idx < len(batch):
                        batch[idx].relevant = verdict.get("relevant", False)
                        batch[idx].relevance_reason = verdict.get("reason", "")

                console.print(f"[green]Batch results:[/green] {[(listing.title, listing.relevant) for listing in batch]}")
                return

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)  # Add jitter to backoff
                    console.print(f"[yellow]Rate limited. Waiting {wait_time:.1f}s before retrying...[/yellow]")
                    await asyncio.sleep(wait_time)
                else:
                    console.print(f"[red]HTTP error: {e}[/red]")
                    break

            except Exception as e:
                if attempt == max_retries - 1:
                    console.print(f"[red]Filter batch error: {e} — keeping batch as-is[/red]")
                    for listing in batch:
                        listing.relevant = True
                else:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)  # Add jitter to backoff
                    console.print(f"[yellow]Retrying in {wait_time:.1f}s due to error: {e}[/yellow]")
                    await asyncio.sleep(wait_time)

    total_batches = (len(listings) + batch_size - 1) // batch_size

    for i in range(0, len(listings), batch_size):
        batch_num = i // batch_size + 1
        batch = listings[i:i + batch_size]
        console.print(f"Judging batch {batch_num}/{total_batches} ({len(batch)} items)...")
        await judge_batch(batch)

        if i + batch_size < len(listings):
            await asyncio.sleep(delay_between_batches)

    if not any(listing.relevant for listing in listings):
        console.print("[yellow]No relevant listings found. Marking all as relevant as fallback.[/yellow]")
        for listing in listings:
            listing.relevant = True
            listing.relevance_reason = "Fallback: No relevant listings identified by the model."

    console.print(f"[green]Final relevant listings:[/green] {[(listing.title, listing.relevant) for listing in listings]}")
    relevant_listings = [listing for listing in listings if listing.relevant]
    console.print(f"\n[bold green]{len(relevant_listings)} relevant listings kept[/bold green]\n")
    return relevant_listings


# ── 3. Product model extraction ────────────────────────────────────────────────

async def extract_product_models(
    listings: list[Listing],
    delay: float = 4.0,
) -> None:
    """
    Extracts product model names from listing titles.
    Processes in one batch if small enough, otherwise splits with delays.
    """
    if not listings:
        return

    batch_size = 10

    for i in range(0, len(listings), batch_size):
        batch = listings[i : i + batch_size]

        items_json = json.dumps(
            [{"id": j, "title": listing.title} for j, listing in enumerate(batch)],
            ensure_ascii=False,
        )

        prompt = f"""From each listing title below, extract the most specific product model name
suitable for a Google search to find professional reviews.
If you cannot determine a specific model, return an empty string.

Return ONLY this JSON format:
{{"results": [{{"id": 0, "model": "..."}}]}}

Listings:
{items_json}"""

        try:
            raw    = await gemini_chat(prompt)
            parsed = extract_json(raw)
            models = []

            if isinstance(parsed, dict):
                models = parsed.get("results", [])
            elif isinstance(parsed, list):
                models = parsed

            for m in models:
                idx = m.get("id")
                if idx is not None and 0 <= idx < len(batch):
                    batch[idx].product_model = m.get("model", "")

        except Exception as e:
            console.print(f"[red]Model extraction error: {e}[/red]")

        if i + batch_size < len(listings):
            await asyncio.sleep(delay)


# ── 4. Review search ───────────────────────────────────────────────────────────

async def search_reviews_duckduckgo(model: str, max_results: int = 3) -> list[dict]:
    """
    Free fallback: scrapes DuckDuckGo HTML search results.
    Targets review-rich sites: Reddit, Notebookcheck, RTINGS, Wirecutter, GSMArena.
    No API key required.
    """
    query = (
        f"{model} review site:reddit.com OR site:notebookcheck.net "
        "OR site:rtings.com OR site:wirecutter.com OR site:gsmarena.com"
    )
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    results = []

    async with httpx.AsyncClient(headers=config.HEADERS, follow_redirects=True, timeout=20) as s:
        try:
            resp = await s.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            for result in soup.select(".result")[:max_results]:
                title_el   = result.select_one(".result__title")
                snippet_el = result.select_one(".result__snippet")
                link_el    = result.select_one(".result__url")

                title   = title_el.get_text(strip=True)   if title_el   else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                link    = link_el.get_text(strip=True)    if link_el    else ""

                if title:
                    results.append({
                        "title":   title,
                        "snippet": snippet,
                        "url":     link if link.startswith("http") else f"https://{link}",
                    })
        except Exception as e:
            console.print(f"[red]DuckDuckGo search error for '{model}': {e}[/red]")

    return results


async def search_reviews_serpapi(model: str, max_results: int = 3) -> list[dict]:
    """
    SerpAPI fallback (free tier: 100 searches/month).
    Only used if SERPAPI_KEY is set.
    """
    query = f"{model} review"
    url   = "https://serpapi.com/search"
    results = []

    async with httpx.AsyncClient(timeout=20) as s:
        try:
            resp = await s.get(url, params={
                "q":       query,
                "api_key": config.SERPAPI_KEY,
                "num":     max_results,
            })
            data = resp.json()

            for r in data.get("organic_results", [])[:max_results]:
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "url":     r.get("link", ""),
                })
        except Exception as e:
            console.print(f"[red]SerpAPI error for '{model}': {e}[/red]")

    return results


async def search_reviews(model: str) -> list[dict]:
    """Route to SerpAPI if key is available, otherwise DuckDuckGo."""
    if config.SERPAPI_KEY:
        return await search_reviews_serpapi(model)
    return await search_reviews_duckduckgo(model)


# ── 5. Review summarization ────────────────────────────────────────────────────

async def search_reviews_for_models(listings: list[Listing]) -> dict[str, list[dict]]:
    """
    Search reviews for each unique product model only once.
    Returns a dict mapping normalized_model → list of review dicts.
    Deduplicates models to avoid redundant searches.
    """
    # Get unique models using normalized names for de-duplication
    # Keep track of both original and normalized names
    seen_normalized = set()
    unique_models = []  # List of (original_model, normalized_model) tuples
    
    for listing in listings:
        if listing.product_model:
            normalized = normalize_model_name(listing.product_model)
            if normalized and normalized not in seen_normalized:
                unique_models.append((listing.product_model, normalized))
                seen_normalized.add(normalized)
    
    if not unique_models:
        return {}
    
    # Extract just the original model names for display
    original_models = [m[0] for m in unique_models]
    console.print(f"  [dim]Searching reviews for {len(unique_models)} unique model(s): {', '.join(original_models)}[/dim]")
    
    # Search for each model concurrently using the original name (for better search results)
    results = await asyncio.gather(*[search_reviews(model[0]) for model in unique_models])
    
    # Map normalized_model → reviews (using normalized key for deduplication)
    reviews_cache = {}
    for (original, normalized), reviews in zip(unique_models, results):
        reviews_cache[normalized] = reviews
    
    if args.debug:
        for (original, normalized), reviews in zip(unique_models, results):
            console.print(f"  [dim]  → {original} ({normalized}): {len(reviews)} review(s)[/dim]")
    
    return reviews_cache


async def aggregate_reviews(listings: list[Listing]) -> None:
    """Search reviews per unique model, generate summaries per model, then copy to listings."""
    console.print("[bold cyan]Step 4: Aggregating reviews...[/bold cyan]")
    
    # Search for reviews once per unique model (using normalized names for de-duplication)
    reviews_cache = await search_reviews_for_models(listings)
    
    # Generate summaries once per unique normalized model
    summary_cache = {}
    
    # Get all unique normalized models from listings
    normalized_models = set()
    for listing in listings:
        if listing.product_model:
            normalized = normalize_model_name(listing.product_model)
            if normalized:
                normalized_models.add(normalized)
    
    for normalized_model in normalized_models:
        # Find the original model name to use for the summary
        # Use the first listing's original model name
        original_model = None
        for listing in listings:
            if listing.product_model and normalize_model_name(listing.product_model) == normalized_model:
                original_model = listing.product_model
                break
        
        if original_model:
            summary_cache[normalized_model] = await generate_summary_for_model(
                original_model, 
                reviews_cache.get(normalized_model, [])
            )
    
    # Assign cached summaries to all listings with that model (using normalized lookup)
    for listing in listings:
        if listing.product_model:
            normalized = normalize_model_name(listing.product_model)
            if normalized and normalized in summary_cache:
                summary_data = summary_cache[normalized]
                listing.review_summary = summary_data["summary"]
                listing.review_links = summary_data["links"]
    
    console.print(f"  Done for {len(listings)} listings ({len(normalized_models)} unique model(s))\n")


async def generate_summary_for_model(model: str, raw_reviews: list[dict]) -> dict[str, any]:
    """Generate a summary for a specific model's reviews. Returns dict with summary and links."""
    if not raw_reviews:
        return {"summary": "No reviews found.", "links": []}
    
    review_links = [r["url"] for r in raw_reviews if r.get("url")]
    
    review_text = "\n\n".join(
        f"Source: {r['title']}\n{r['snippet']}" for r in raw_reviews
    )

    prompt = f"""Based on the review excerpts below for "{model}",
write a 2-3 sentence summary covering:
1. Key strengths
2. Main weaknesses
3. Who it is best suited for

Be concise and factual. Do not invent information not present in the excerpts.

Return ONLY a JSON object:
{{"summary": "your summary here"}}

Review excerpts:
{review_text}"""

    try:
        raw    = await gemini_chat(prompt, temperature=0.2)
        parsed = extract_json(raw)
        if isinstance(parsed, dict):
            summary = parsed.get("summary", "Summary unavailable.")
        else:
            summary = "Summary unavailable."
    except Exception as e:
        summary = f"Error generating summary: {e}"
    
    return {"summary": summary, "links": review_links}


# ── 5. Fetch descriptions for relevant items ───────────────────────────────────

async def fetch_description_dba(listing: Listing) -> None:
    """Fetch description from DBA product page."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(listing.url, headers=config.HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            text = ""
            
            # Try JSON-LD script tag first (DBA serves description here)
            script = soup.find("script", type="application/ld+json")
            if script:
                import json
                try:
                    data = json.loads(script.string)
                    text = data.get("description", "") or ""
                    # Try to get date from JSON-LD
                    if not listing.date_posted:
                        date_str = data.get("datePosted", "") or data.get("datePublished", "") or data.get("dateCreated", "")
                        if date_str:
                            listing.date_posted = date_str.split("T")[0]  # Keep only date part
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            # Fallback to div-based selectors
            if not text or len(text) <= 10:
                desc_elem = soup.find("div", class_=re.compile(r"description|excerpt|summary", re.I))
                if desc_elem:
                    text = desc_elem.get_text(strip=True)
                elif not text:
                    desc_elem = soup.find(["p", "div"], attrs={"data-testid": re.compile(r"description", re.I)})
                    if desc_elem:
                        text = desc_elem.get_text(strip=True)
            
            # Try to extract date from the page
            if not listing.date_posted:
                date_el = soup.find(["span", "div", "time"], class_=re.compile(r"date|time|posted|published|oprettet|dato", re.I))
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    # Clean up date text (remove "Oprettet", "Posted", etc.)
                    date_text = re.sub(r'^(Oprettet|Posted|Created|Dato):?\s*', '', date_text, flags=re.I)
                    if date_text and len(date_text) < 50:
                        listing.date_posted = date_text
                else:
                    # Try time tag
                    time_el = soup.find("time")
                    if time_el:
                        listing.date_posted = time_el.get("datetime", "").split("T")[0]
            
            if text and len(text) > 10:
                listing.description = text[:500]  # Limit to 500 chars
                if args.debug:
                    console.print(f"  [dim]DBA desc: {text[:100]}...[/dim]")
    except Exception as e:
        if args.debug:
            console.print(f"  [dim]DBA desc fetch error: {e}[/dim]")


async def fetch_description_tradera(listing: Listing) -> None:
    """Fetch description from Tradera product page."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(listing.url, headers=config.HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Look for description sections
            desc_elem = soup.find("div", class_=re.compile(r"description|item.*desc", re.I))
            if not desc_elem:
                # Try finding a section with "Description" heading
                heading = soup.find(["h2", "h3"], string=re.compile(r"description", re.I))
                if heading:
                    desc_elem = heading.find_next("div", class_=re.compile(r"content|text|desc", re.I))
            
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if text and len(text) > 10:
                    listing.description = text[:500]
                    if args.debug:
                        console.print(f"  [dim]Tradera desc: {text[:100]}...[/dim]")
            
            # Try to extract date from the page
            if not listing.date_posted:
                date_el = soup.find(["span", "div", "time"], class_=re.compile(r"date|time|posted|published|skapat|upp skapad", re.I))
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    date_text = re.sub(r'^(Publicerad|Skapad|Posted|Created):?\s*', '', date_text, flags=re.I)
                    if date_text and len(date_text) < 50:
                        listing.date_posted = date_text
                else:
                    time_el = soup.find("time")
                    if time_el:
                        listing.date_posted = time_el.get("datetime", "").split("T")[0]
    except Exception as e:
        if args.debug:
            console.print(f"  [dim]Tradera desc fetch error: {e}[/dim]")


async def fetch_description_vinted(listing: Listing) -> None:
    """Fetch description from Vinted product page if not already present."""
    try:
        if listing.description and listing.description != "...":
            # Already has description
            return
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(listing.url, headers=config.HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            text = ""
            
            # Try JSON-LD script tag first (Vinted serves description here)
            script = soup.find("script", type="application/ld+json")
            if script:
                import json
                try:
                    data = json.loads(script.string)
                    text = data.get("description", "") or ""
                    # Try to get date from JSON-LD
                    if not listing.date_posted:
                        date_str = data.get("datePosted", "") or data.get("datePublished", "") or data.get("dateCreated", "")
                        if date_str:
                            listing.date_posted = date_str.split("T")[0]
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            # Fallback to div-based selectors
            if not text or len(text) <= 10:
                desc_elem = soup.find("div", attrs={"data-testid": re.compile(r"item.*description", re.I)})
                if desc_elem:
                    text = desc_elem.get_text(strip=True)
                elif not text:
                    desc_elem = soup.find("div", class_=re.compile(r"description", re.I))
                    if desc_elem:
                        text = desc_elem.get_text(strip=True)
            
            # Try to extract date from the page
            if not listing.date_posted:
                date_el = soup.find(["span", "div", "time"], class_=re.compile(r"date|time|posted|published|oprettet|dato", re.I))
                if date_el:
                    date_text = date_el.get_text(strip=True)
                    date_text = re.sub(r'^(Oprettet|Posted|Created|Dato):?\s*', '', date_text, flags=re.I)
                    if date_text and len(date_text) < 50:
                        listing.date_posted = date_text
                else:
                    time_el = soup.find("time")
                    if time_el:
                        listing.date_posted = time_el.get("datetime", "").split("T")[0]
            
            if text and len(text) > 10:
                listing.description = text[:500]
                if args.debug:
                    console.print(f"  [dim]Vinted desc: {text[:100]}...[/dim]")
    except Exception as e:
        if args.debug:
            console.print(f"  [dim]Vinted desc fetch error: {e}[/dim]")


async def fetch_descriptions(listings: list[Listing]) -> None:
    """Fetch descriptions from product pages for relevant listings."""
    console.print("[bold cyan]Step 4.5: Fetching descriptions for relevant items...[/bold cyan]")
    
    tasks = []
    for listing in listings:
        if listing.platform == "DBA":
            tasks.append(fetch_description_dba(listing))
        elif listing.platform == "Tradera":
            tasks.append(fetch_description_tradera(listing))
        elif listing.platform == "Vinted":
            tasks.append(fetch_description_vinted(listing))
    
    if tasks:
        await asyncio.gather(*tasks)
        console.print(f"  Done for {len(listings)} listings\n")
    else:
        console.print("  No listings to fetch descriptions for\n")


# ── 6. Scoring & ranking ───────────────────────────────────────────────────────

async def score_and_rank(listings: list[Listing], user_query: str) -> list[Listing]:
    """
    Ask Gemini to score each listing 1–10 based on price, relevance,
    description quality, and review quality. Falls back to a simple price-based sort on error.
    If --no-score is set, sorts by price instead.
    """
    if not listings:
        return listings

    # Skip scoring if disabled (Gemini quota exceeded, etc.)
    if args.no_score:
        console.print("[bold cyan]Step 6: Sorting by price (--no-score flag)[/bold cyan]")
        # Sort by price ascending (cheapest first)
        listings.sort(key=lambda l: l.price if l.price > 0 else float('inf'))
        for listing in listings:
            listing.score = 10.0 - min(9.0, listing.price / 100)  # Rough score based on price
        console.print()
        return listings

    # Warn about suspiciously high prices
    for listing in listings:
        if listing.price > 10000:
            console.print(f"[yellow]⚠️  Suspicious price: {listing.title} ({listing.platform}): {listing.price} {listing.currency}[/yellow]")

    items_json = json.dumps(
        [
            {
                "id":             i,
                "title":          l.title,
                "description":    l.description,
                "price":          l.price,
                "currency":       l.currency,
                "platform":       l.platform,
                "review_summary": l.review_summary,
            }
            for i, l in enumerate(listings)
        ],
        ensure_ascii=False,
    )

    prompt = f"""The user is looking for: "{user_query}"

Score each of the following second-hand listings from 1 to 10 based on:
- Value for money (price vs. typical market price)
- How well it matches the user's stated need
- Condition and quality indicators from the title AND description (mentions of new/unused, damage, original packaging, accessories included, etc.)
- Review quality (positive reviews = higher score)

Pay special attention to the description field which contains important details about the item's condition and what's included.

Return ONLY a JSON object:
{{"scores": [{{"id": 0, "score": 7.5, "reason": "one sentence"}}]}}

Listings:
{items_json}"""

    console.print("[bold cyan]Step 6: Scoring and ranking...[/bold cyan]")
    try:
        raw    = await gemini_chat(prompt, temperature=0.1)
        parsed = extract_json(raw)
        scores = parsed.get("scores", []) if isinstance(parsed, dict) else []

        for s in scores:
            idx = s.get("id")
            if idx is not None and 0 <= idx < len(listings):
                listings[idx].score = float(s.get("score", 0))
                listings[idx].score_reason = s.get("reason", "")
    except Exception as e:
        console.print(f"[red]Scoring error: {e} — falling back to price sort[/red]")
        # Fallback: score inversely by price (cheaper = higher score)
        prices = [l.price for l in listings if l.price > 0]
        if prices:
            max_p = max(prices)
            for l in listings:
                l.score = round(10 * (1 - l.price / max_p), 1) if l.price > 0 else 5.0

    listings.sort(key=lambda l: l.score, reverse=True)
    return listings


# ── 7. Output ──────────────────────────────────────────────────────────────────

def display_results(listings: list[Listing], user_query: str, skip_reviews: bool = False) -> None:
    """Render a rich terminal report of the ranked listings."""
    console.print()
    console.rule(f"[bold green]Results for: {user_query}[/bold green]")
    console.print()

    if not listings:
        console.print("[yellow]No relevant listings found.[/yellow]")
        return

    for rank, listing in enumerate(listings, start=1):
        # Header
        console.print(
            f"[bold white]#{rank}[/bold white]  "
            f"[bold cyan]{listing.title}[/bold cyan]  "
            f"[dim]({listing.platform})[/dim]"
        )

        # Price and score row
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column(style="bold yellow")
        table.add_column()
        table.add_row("Price",   f"{listing.price:,.0f} {listing.currency}")
        table.add_row("Score",   f"{listing.score:.1f} / 10")
        if listing.score_reason:
            table.add_row("Reason",  listing.score_reason)
        if listing.date_posted:
            table.add_row("Posted",  listing.date_posted)
        if not skip_reviews and listing.product_model:
            table.add_row("Model",   listing.product_model)
        table.add_row("Link",    listing.url)
        console.print(table)

        # Review summary
        if listing.review_summary:
            console.print(f"  [bold]Reviews:[/bold] {listing.review_summary}")

        # Review links
        if listing.review_links:
            console.print("  [bold]Sources:[/bold]")
            for link in listing.review_links[:3]:
                console.print(f"    • {link}")

        console.print()

    console.rule()


# ── Entry point ────────────────────────────────────────────────────────────────

async def research(user_query: str, max_per_platform: int = config.DEFAULT_MAX_RESULTS, skip_reviews: bool = False) -> None:
    console.print(f"\n[bold green]Researching:[/bold green] {user_query}\n")
    console.rule()

    # Stage 1 — scrape
    console.print("[bold cyan]Step 1: Scraping listings...[/bold cyan]")
    all_listings = await scrape_all(user_query, max_results=max_per_platform)

    if not all_listings:
        console.print("[red]No listings found. Check your scraper selectors.[/red]")
        return

    # Stage 2 — convert prices to target currency
    await convert_prices(all_listings, args.currency)

    # Stage 3 — filter
    relevant = await filter_listings(all_listings, user_query)

    if not relevant:
        console.print("[yellow]No relevant listings after filtering.[/yellow]")
        return

    # Stage 4 — fetch descriptions for relevant items only
    await fetch_descriptions(relevant)

    # Stage 4.6 — second LLM filter pass with full descriptions
    console.print("[bold cyan]Step 4.6: Second filtering pass with full descriptions...[/bold cyan]")
    relevant = await filter_listings(relevant, user_query)

    # Stage 5 — extract models and reviews (optional)
    if not skip_reviews:
        await extract_product_models(relevant)
        await aggregate_reviews(relevant)
    else:
        console.print("[bold cyan]Step 5: Skipping review extraction (--no-reviews flag)[/bold cyan]\n")

    # Stage 6 — score & rank
    ranked = await score_and_rank(relevant, user_query)

    # Stage 7 — display
    display_results(ranked, user_query, skip_reviews=skip_reviews)


if __name__ == "__main__":
    import sys

    query = args.query
    skip_reviews = args.no_reviews
    asyncio.run(research(query, skip_reviews=skip_reviews))