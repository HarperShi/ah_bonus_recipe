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

Install the React frontend dependencies:

```bash
cd frontend
npm install
cd ..
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

Generate recipes from the latest weekly dataset:

```bash
uv run ah-bonus generate-recipes --servings 2 --recipe-count 3 --minimum-bonus-products 2
```

Useful preference options:

```bash
uv run ah-bonus generate-recipes \
  --allergy milk \
  --dislike coriander \
  --cuisine Italian \
  --main-ingredient seafood \
  --diet vegetarian \
  --max-cooking-minutes 35
```

This writes `data/processed/latest_recipes.json`. The OpenAI API proposes structured recipes; local code validates bonus product IDs, calculates AH Bonus savings from pack counts and promotion labels, and reports known nutrition from AH product data alongside the model's full-meal nutrition estimate.

Run the React/Vite website. The frontend uses Tailwind and local Shadcn-style UI primitives:

```bash
uv run ah-bonus serve-api --reload
```

In another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` requests to the Python backend on `http://127.0.0.1:8000`.

## Next Milestones

1. Add SQLite or Parquet persistence if JSON becomes too slow.
2. Improve package-size parsing and serving-size conversions for more nutrition rows.
3. Add retry/repair loops when OpenAI returns recipes that do not meet validation.
4. Add a production Docker setup for the API and Vite build.

## Weekly Schedule

AH metadata exposes concrete bonus start and end dates. Schedule the full scraper every Sunday, but store the AH-provided dates rather than assuming them.

For local cron in Amsterdam time:

```cron
0 8 * * 0 cd /path/to/ah_bonus_recipe && uv run ah-bonus scrape-week
```
