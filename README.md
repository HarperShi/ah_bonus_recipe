# AH Bonus Recipe

Python-first project for collecting weekly Albert Heijn Bonus products and using them to generate recipe ideas with savings and nutrition estimates.

## Current Status

This repository is a skeleton plus a working scraper discovery path.

Confirmed discovery:

- AH mobile API supports anonymous tokens.
- Weekly Bonus metadata is available from `/mobile-services/bonuspage/v3/metadata`.
- Category sections are available from metadata URLs under `/mobile-services/bonuspage/v2/section`.
- Group Bonus cards can be expanded through `/graphql` with `bonusPromotions`.
- Product detail pages are available from `/mobile-services/product/detail/v4/fir/{webshop_id}` and include `tradeItem` nutrition, ingredients, allergens, servings, and measurements.

## Setup

Install `uv` if needed, then run:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run pytest
```

Run AH discovery:

```bash
uv run ah-bonus discover
```

This writes timestamped artifacts to `data/discovery/`.

Run the weekly scraper:

```bash
uv run ah-bonus scrape-week
```

This writes raw AH payloads to `data/raw/<week_start>_to_<week_end>/` and normalized outputs to:

- `data/processed/bonus_week_<week_start>_to_<week_end>.json`
- `data/processed/latest_bonus_week.json`
- `data/processed/latest_products.json`

For a quick smoke test without scraping every product:

```bash
uv run ah-bonus scrape-week --max-products 10
```

Generate a quality and discount coverage report:

```bash
uv run ah-bonus quality-report
```

This writes `data/processed/latest_quality_report.json`, including field coverage, products with missing nutrition/allergen/ingredient/portion data, discount label coverage, and sample one-pack savings estimates.

## Next Milestones

1. Add SQLite or Parquet persistence if JSON becomes too slow.
2. Add recipe validation and per-recipe nutrition totals.
3. Connect recipe ingredient quantities to the discount engine.
4. Run the Streamlit app with `uv run streamlit run src/ah_bonus_recipe/web/streamlit_app.py`.

## Weekly Schedule

AH metadata exposes concrete bonus start and end dates. Schedule the full scraper every Sunday, but store the AH-provided dates rather than assuming them.

For local cron in Amsterdam time:

```cron
0 8 * * 0 cd /path/to/ah_bonus_recipe && uv run ah-bonus scrape-week
```
