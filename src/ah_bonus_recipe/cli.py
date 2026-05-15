from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from ah_bonus_recipe.config import DISCOVERY_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from ah_bonus_recipe.scraper.discover import run_discovery
from ah_bonus_recipe.scraper.weekly import DEFAULT_PROMOTION_TYPES, scrape_bonus_week

app = typer.Typer(help="AH Bonus recipe project tools.")


@app.command()
def discover(
    output_dir: Path = typer.Option(DISCOVERY_DIR, help="Directory for discovery artifacts."),
    sample_category: str | None = typer.Option(None, help="Category name to sample."),
    max_chunks: int | None = typer.Option(None, help="Limit downloaded JS chunks for quicker runs."),
) -> None:
    """Capture AH web/API discovery artifacts."""

    summary = run_discovery(output_dir, sample_category=sample_category, max_chunks=max_chunks)
    print(f"[green]Discovery complete[/green]: {summary['run_dir']}")
    print(f"Current period: {summary['api']['current_period']}")
    if sample := summary["api"].get("sample_product_detail"):
        print(f"Sample product detail: {sample}")


@app.command("scrape-week")
def scrape_week(
    raw_output_dir: Path = typer.Option(RAW_DATA_DIR, help="Directory for raw weekly AH payloads."),
    processed_output_dir: Path = typer.Option(
        PROCESSED_DATA_DIR,
        help="Directory for normalized datasets.",
    ),
    period: str = typer.Option(
        "current",
        help="Bonus period to scrape: current, next, or a bonusStartDate like 2026-05-11.",
    ),
    promotion_type: list[str] = typer.Option(
        list(DEFAULT_PROMOTION_TYPES),
        "--promotion-type",
        help="Promotion type to include. Repeat for multiple values.",
    ),
    include_store_only: bool = typer.Option(False, help="Include store-only promotions."),
    filter_unavailable_group_products: bool = typer.Option(
        False,
        help="Ask GraphQL to filter unavailable products when expanding groups.",
    ),
    max_products: int | None = typer.Option(
        None,
        help="Development/testing limit. Omit for a full scrape.",
    ),
    request_delay_seconds: float = typer.Option(
        0.05,
        help="Small delay between product detail requests.",
    ),
) -> None:
    """Scrape a full weekly AH Bonus dataset."""

    summary = scrape_bonus_week(
        raw_output_dir=raw_output_dir,
        processed_output_dir=processed_output_dir,
        period=period,
        promotion_types=tuple(promotion_type),
        include_store_only=include_store_only,
        filter_unavailable_group_products=filter_unavailable_group_products,
        max_products=max_products,
        request_delay_seconds=request_delay_seconds,
    )
    print("[green]Weekly scrape complete[/green]")
    print(f"Week: {summary['week_start']} to {summary['week_end']}")
    print(f"Promotions: {summary['promotion_count']}")
    print(f"Products: {summary['product_count']}")
    print(f"Raw data: {summary['raw_dir']}")
    print(f"Processed dataset: {summary['processed_week_path']}")
    if summary["failed_sections"] or summary["failed_groups"] or summary["failed_products"]:
        print("[yellow]Some requests failed; see raw summary.json for details.[/yellow]")


if __name__ == "__main__":
    app()
