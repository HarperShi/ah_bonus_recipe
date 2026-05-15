from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from ah_bonus_recipe.config import DISCOVERY_DIR
from ah_bonus_recipe.scraper.discover import run_discovery

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
def scrape_week() -> None:
    """Placeholder for the weekly full scraper."""

    print(
        "[yellow]Not implemented yet.[/yellow] "
        "Next step: normalize every category section, expand every bonus group, "
        "fetch each product detail, and write BonusWeekDataset."
    )


if __name__ == "__main__":
    app()
