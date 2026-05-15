from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from ah_bonus_recipe.models import BonusProduct, RecipePreferences


RECIPE_JSON_SCHEMA: dict[str, Any] = {
    "name": "weekly_bonus_recipes",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "recipes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "cuisine": {"type": "string"},
                        "servings": {"type": "integer"},
                        "bonus_product_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "name": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "unit": {"type": "string"},
                                    "bonus_product_id": {"type": ["integer", "null"]},
                                },
                                "required": ["name", "quantity", "unit", "bonus_product_id"],
                            },
                        },
                        "prep": {"type": "array", "items": {"type": "string"}},
                        "steps": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "title",
                        "cuisine",
                        "servings",
                        "bonus_product_ids",
                        "ingredients",
                        "prep",
                        "steps",
                        "notes",
                    ],
                },
            }
        },
        "required": ["recipes"],
    },
    "strict": True,
}


def generate_recipes(
    preferences: RecipePreferences,
    bonus_products: list[BonusProduct],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """Generate recipe candidates as JSON.

    Savings and final nutrition totals should be calculated by local code after
    this returns. The model only proposes recipes and quantities.
    """

    client = OpenAI()
    model = model or os.getenv("OPENAI_RECIPE_MODEL", "gpt-5.4-mini")
    product_payload = [
        {
            "webshop_id": product.webshop_id,
            "title": product.title,
            "brand": product.brand,
            "category": product.category,
            "sales_unit_size": product.sales_unit_size,
            "bonus_mechanism": product.bonus_mechanism,
            "allergens": [
                {"name": allergen.name, "containment": allergen.containment}
                for allergen in product.allergens
                if allergen.containment != "FREE_FROM"
            ],
        }
        for product in bonus_products
    ]

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Create practical home-cooking recipes from this week's AH Bonus products. "
                    "Return only valid JSON matching the schema. Use at least the requested "
                    "minimum number of distinct bonus products per recipe. Do not include "
                    "ingredients that conflict with user allergies or dislikes."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "preferences": preferences.model_dump(),
                        "bonus_products": product_payload,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        text={"format": {"type": "json_schema", **RECIPE_JSON_SCHEMA}},
    )
    return json.loads(response.output_text)
