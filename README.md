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

## Next Milestones

1. Convert all raw AH payloads into a normalized `BonusWeekDataset`.
2. Add persistence to SQLite or Parquet.
3. Implement the weekly scraper command behind `ah-bonus scrape-week`.
4. Add recipe validation, savings calculation, and nutrition totals.
5. Run the Streamlit app with `uv run streamlit run src/ah_bonus_recipe/web/streamlit_app.py`.

## Weekly Schedule

AH metadata exposes concrete bonus start and end dates. Schedule the full scraper every Sunday, but store the AH-provided dates rather than assuming them.

For local cron in Amsterdam time:

```cron
0 8 * * 0 cd /path/to/ah_bonus_recipe && uv run ah-bonus scrape-week
```
