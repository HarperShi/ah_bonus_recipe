from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from ah_bonus_recipe.config import DISCOVERY_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from ah_bonus_recipe.models import RecipePreferences
from ah_bonus_recipe.quality import DEFAULT_DATASET_PATH, DEFAULT_REPORT_PATH, generate_quality_report
from ah_bonus_recipe.recipes.generator import (
    DEFAULT_CANDIDATE_LIMIT,
    DEFAULT_DATASET_PATH as DEFAULT_RECIPE_DATASET_PATH,
    DEFAULT_RECIPE_OUTPUT_PATH,
    RecipeGenerationError,
    generate_recipe_plan,
)
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


@app.command("quality-report")
def quality_report(
    dataset_path: Path = typer.Option(DEFAULT_DATASET_PATH, help="Processed BonusWeekDataset JSON."),
    output_path: Path = typer.Option(DEFAULT_REPORT_PATH, help="Output path for quality report JSON."),
    max_issue_products: int | None = typer.Option(
        None,
        help="Limit products_with_issues in the report. Omit to include all.",
    ),
) -> None:
    """Generate dataset quality and discount coverage report."""

    report = generate_quality_report(
        dataset_path=dataset_path,
        output_path=output_path,
        max_issue_products=max_issue_products,
    )
    field_coverage = report["field_coverage"]
    discount_support = report["discount_support"]
    print("[green]Quality report complete[/green]")
    print(f"Products: {report['product_count']}")
    print(f"Promotions: {report['promotion_count']}")
    print(f"Products with issues: {report['products_with_issues_count']}")
    print(f"Nutrition present: {field_coverage['nutrition']['present']}")
    print(f"Allergens present: {field_coverage['allergens']['present']}")
    print(f"Discounts supported: {discount_support.get('supported', 0)}")
    print(f"Discounts unsupported: {discount_support.get('unsupported', 0)}")
    print(f"Report: {output_path}")


@app.command("generate-recipes")
def generate_recipes_command(
    dataset_path: Path = typer.Option(
        DEFAULT_RECIPE_DATASET_PATH,
        help="Processed BonusWeekDataset JSON.",
    ),
    output_path: Path = typer.Option(
        DEFAULT_RECIPE_OUTPUT_PATH,
        help="Output path for generated recipes JSON.",
    ),
    servings: int = typer.Option(2, min=1, max=20, help="Number of people."),
    recipe_count: int = typer.Option(3, min=1, max=10, help="Number of recipes to generate."),
    minimum_bonus_products: int = typer.Option(
        2,
        min=1,
        max=10,
        help="Minimum distinct bonus products per recipe.",
    ),
    allergy: list[str] | None = typer.Option(
        None,
        "--allergy",
        help="Allergy to avoid. Repeat for multiple values.",
    ),
    dislike: list[str] | None = typer.Option(
        None,
        "--dislike",
        help="Ingredient to avoid. Repeat for multiple values.",
    ),
    cuisine: str | None = typer.Option(None, help="Cuisine preference."),
    main_ingredient: list[str] | None = typer.Option(
        None,
        "--main-ingredient",
        help="Preferred main ingredient. Repeat for multiple values.",
    ),
    diet: str | None = typer.Option(None, help="Diet preference, e.g. vegetarian or vegan."),
    meal_type: str | None = typer.Option("dinner", help="Meal type."),
    max_cooking_minutes: int | None = typer.Option(None, min=5, max=240, help="Time limit."),
    skill_level: str | None = typer.Option(None, help="Cooking skill level."),
    budget: str | None = typer.Option(None, help="Budget preference."),
    spice_level: str | None = typer.Option(None, help="Spice preference."),
    equipment: list[str] | None = typer.Option(
        None,
        "--equipment",
        help="Available equipment. Repeat for multiple values.",
    ),
    candidate_limit: int = typer.Option(
        DEFAULT_CANDIDATE_LIMIT,
        min=10,
        max=200,
        help="Maximum filtered bonus products sent to OpenAI.",
    ),
    model: str | None = typer.Option(None, help="OpenAI model override."),
) -> None:
    """Generate recipes from the current weekly Bonus dataset."""

    preferences = RecipePreferences(
        servings=servings,
        allergies=allergy or [],
        disliked_ingredients=dislike or [],
        cuisine=cuisine,
        main_ingredients=main_ingredient or [],
        diet=diet,
        max_cooking_minutes=max_cooking_minutes,
        skill_level=skill_level,
        budget=budget,
        meal_type=meal_type,
        spice_level=spice_level,
        equipment=equipment or [],
        recipe_count=recipe_count,
        minimum_bonus_products=minimum_bonus_products,
    )
    try:
        result = generate_recipe_plan(
            preferences,
            dataset_path=dataset_path,
            output_path=output_path,
            model=model,
            candidate_limit=candidate_limit,
        )
    except RecipeGenerationError as exc:
        raise typer.BadParameter(str(exc)) from exc

    print("[green]Recipe generation complete[/green]")
    print(f"Week: {result.week_start} to {result.week_end}")
    print(f"Candidate products sent to OpenAI: {result.candidate_product_count}")
    print(f"Recipes: {len(result.recipes)}")
    for recipe in result.recipes:
        print(
            f"- {recipe.title}: saves €{recipe.savings.savings:.2f} "
            f"using {len(recipe.bonus_product_uses)} bonus ingredient line(s)"
        )
    if result.warnings:
        print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            print(f"- {warning}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    app()
