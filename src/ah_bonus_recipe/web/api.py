from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from ah_bonus_recipe.config import ROOT_DIR
from ah_bonus_recipe.models import BonusWeekDataset, RecipeGenerationResult, RecipePreferences
from ah_bonus_recipe.recipes.generator import (
    DEFAULT_CANDIDATE_LIMIT,
    DEFAULT_DATASET_PATH,
    DEFAULT_RECIPE_OUTPUT_PATH,
    RecipeGenerationError,
    generate_recipe_plan,
    load_bonus_week_dataset,
    select_candidate_products,
)


class DatasetStatus(BaseModel):
    dataset_exists: bool
    week_start: str | None = None
    week_end: str | None = None
    product_count: int = 0
    promotion_count: int = 0
    candidate_product_count: int = 0
    latest_recipes_exists: bool = False
    openai_configured: bool = False


class RecipeGenerationRequest(BaseModel):
    preferences: RecipePreferences
    candidate_limit: int = Field(default=DEFAULT_CANDIDATE_LIMIT, ge=10, le=200)


app = FastAPI(title="AH Bonus Recipe API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status", response_model=DatasetStatus)
def get_status() -> DatasetStatus:
    if not DEFAULT_DATASET_PATH.exists():
        return DatasetStatus(
            dataset_exists=False,
            latest_recipes_exists=DEFAULT_RECIPE_OUTPUT_PATH.exists(),
            openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        )
    dataset = load_bonus_week_dataset(DEFAULT_DATASET_PATH)
    return dataset_status(dataset)


@app.get("/api/latest-recipes")
def get_latest_recipes() -> dict[str, Any]:
    if not DEFAULT_RECIPE_OUTPUT_PATH.exists():
        raise HTTPException(status_code=404, detail="No generated recipes found yet.")
    return json.loads(DEFAULT_RECIPE_OUTPUT_PATH.read_text(encoding="utf-8"))


@app.post("/api/recipes")
def generate_recipes(request: RecipeGenerationRequest) -> dict[str, Any]:
    try:
        result = generate_recipe_plan(
            request.preferences,
            dataset_path=DEFAULT_DATASET_PATH,
            output_path=DEFAULT_RECIPE_OUTPUT_PATH,
            candidate_limit=request.candidate_limit,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="No weekly dataset found. Run `uv run ah-bonus scrape-week` first.",
        ) from exc
    except RecipeGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return result.model_dump(mode="json")


def dataset_status(dataset: BonusWeekDataset) -> DatasetStatus:
    default_preferences = RecipePreferences(servings=2, recipe_count=3, minimum_bonus_products=2)
    return DatasetStatus(
        dataset_exists=True,
        week_start=str(dataset.week_start),
        week_end=str(dataset.week_end),
        product_count=len(dataset.products),
        promotion_count=len(dataset.promotions),
        candidate_product_count=len(
            select_candidate_products(
                dataset.products,
                default_preferences,
                limit=DEFAULT_CANDIDATE_LIMIT,
            )
        ),
        latest_recipes_exists=DEFAULT_RECIPE_OUTPUT_PATH.exists(),
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
    )


def load_recipe_result(path: Path = DEFAULT_RECIPE_OUTPUT_PATH) -> RecipeGenerationResult:
    return RecipeGenerationResult.model_validate_json(path.read_text(encoding="utf-8"))


frontend_dist = ROOT_DIR / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
