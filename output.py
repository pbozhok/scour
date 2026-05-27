"""
Output - renders results in a rich terminal format.
"""

from rich import box
from rich.console import Console
from rich.table import Table

from models import Listing
from core.module import PipelineContext

console = Console()


def display_results(listings: list[Listing], user_query: str, skip_reviews: bool = False) -> None:
    """
    Render a rich terminal report of the ranked listings.
    
    Args:
        listings: List of listings to display
        user_query: The original search query
        skip_reviews: Whether reviews were skipped
    """
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
        if not skip_reviews and listing.product_model:
            table.add_row("Model",   listing.product_model)
        if listing.date_posted:
            table.add_row("Date",    listing.date_posted)
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


def display_results_from_context(
    context: PipelineContext,
    user_query: str,
    skip_reviews: bool = False
) -> None:
    """
    Render results from a PipelineContext.
    
    This is the new display function for the modular pipeline.
    
    Args:
        context: The pipeline context containing results
        user_query: The original search query
        skip_reviews: Whether reviews were skipped
    """
    # Display errors first if any
    if context.errors:
        console.print(f"\n[bold red]Pipeline completed with {len(context.errors)} error(s)[/bold red]")
        for error in context.errors:
            console.print(f"  [red]✗ {error.module_name}: {error.message}[/red]")
        console.print()
    
    # Display results
    display_results(context.listings, user_query, skip_reviews=skip_reviews)
    
    # Display metadata
    if context.metadata:
        console.print("\n[bold]Pipeline Metadata:[/bold]")
        for key, value in context.metadata.items():
            if key != "pipeline_start":
                console.print(f"  {key}: {value}")
