from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ah_bonus_recipe.models import (
    AllergenStatus,
    BonusProduct,
    BonusPromotion,
    BonusWeekDataset,
    DiscountLabel,
    NutritionValue,
    RecipePreferences,
)
from ah_bonus_recipe.recipes.generator import generate_recipe_plan, select_candidate_products
from ah_bonus_recipe.recipes.nutrition import parse_sales_unit_size


def test_select_candidate_products_filters_non_food_and_allergies() -> None:
    products = [
        bonus_product(1, title="AH Pasta", category="Pasta, rijst, wereldkeuken"),
        bonus_product(2, title="Shampoo", category="Drogisterij"),
        bonus_product(
            3,
            title="Roomsaus",
            category="Soepen, sauzen, kruiden, olie",
            allergens=[AllergenStatus(code="AM", name="Melk", containment="CONTAINS")],
        ),
    ]

    selected = select_candidate_products(
        products,
        RecipePreferences(servings=2, allergies=["milk"], recipe_count=1),
    )

    assert [product.webshop_id for product in selected] == [1]


def test_generate_recipe_plan_enriches_savings_and_known_nutrition(tmp_path: Path) -> None:
    dataset = BonusWeekDataset(
        week_start=date(2026, 5, 11),
        week_end=date(2026, 5, 17),
        scraped_at=datetime.now(timezone.utc),
        source_url="https://www.ah.nl/bonus",
        products=[
            bonus_product(1, title="AH Pasta", price_before_bonus=4.0, current_price=3.0),
            bonus_product(2, title="AH Tomatensaus", price_before_bonus=2.0, current_price=1.5),
        ],
        promotions=[
            BonusPromotion(
                id="promo-1",
                title="1 + 1 gratis",
                discount_labels=[
                    DiscountLabel.model_validate(
                        {"code": "DISCOUNT_X_PLUS_Y_FREE", "count": 1, "free_count": 1}
                    )
                ],
                product_ids=[1, 2],
            )
        ],
    )
    dataset_path = tmp_path / "bonus_week.json"
    dataset_path.write_text(
        json.dumps(dataset.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    client = FakeOpenAIClient(
        {
            "recipes": [
                {
                    "title": "Bonus Tomato Pasta",
                    "cuisine": "Italian",
                    "servings": 2,
                    "total_time_minutes": 25,
                    "bonus_product_ids": [1, 2],
                    "ingredients": [
                        {
                            "name": "AH Pasta",
                            "quantity": 200,
                            "unit": "g",
                            "bonus_product_id": 1,
                            "packages_to_buy": 1,
                        },
                        {
                            "name": "AH Tomatensaus",
                            "quantity": 100,
                            "unit": "g",
                            "bonus_product_id": 2,
                            "packages_to_buy": 1,
                        },
                        {
                            "name": "Salt",
                            "quantity": 1,
                            "unit": "pinch",
                            "bonus_product_id": None,
                            "packages_to_buy": 0,
                        },
                    ],
                    "prep": ["Boil water."],
                    "steps": ["Cook pasta.", "Warm sauce."],
                    "notes": ["Use salt to taste."],
                    "estimated_nutrition_total": nutrition_payload(420, 16),
                    "estimated_nutrition_per_serving": nutrition_payload(210, 8),
                }
            ]
        }
    )

    result = generate_recipe_plan(
        RecipePreferences(servings=2, recipe_count=1, minimum_bonus_products=2),
        dataset_path=dataset_path,
        client=client,
    )

    recipe = result.recipes[0]
    assert result.candidate_product_count == 2
    assert recipe.savings.baseline_total == 6.0
    assert recipe.savings.promo_total == 3.0
    assert recipe.savings.savings == 3.0
    assert recipe.savings.notes == [
        "1+1 gratis is prorated in the recipe savings; "
        "buy at least 2 qualifying products to activate this bonus."
    ]
    assert recipe.ingredients[-1].model_dump(mode="json")["packages_to_buy"] == "-"
    assert recipe.nutrition_report.known_bonus_total["energy_kcal"] == 300.0
    assert recipe.nutrition_report.known_bonus_total["protein_g"] == 12.0
    assert recipe.validation_warnings == []


def test_parse_sales_unit_size_handles_multipacks_and_decimal_commas() -> None:
    assert parse_sales_unit_size("6 x 0,33 l") == (1980.0, "ml")
    assert parse_sales_unit_size("2 x 250 g") == (500.0, "g")


class FakeOpenAIClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.responses = FakeResponses(payload)


class FakeResponses:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return FakeOpenAIResponse(self.payload)


class FakeOpenAIResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.output_text = json.dumps(payload)


def bonus_product(
    webshop_id: int,
    *,
    title: str,
    category: str = "Pasta, rijst, wereldkeuken",
    price_before_bonus: float = 2.0,
    current_price: float = 1.0,
    allergens: list[AllergenStatus] | None = None,
) -> BonusProduct:
    return BonusProduct(
        webshop_id=webshop_id,
        title=title,
        category=category,
        sales_unit_size="500 g",
        price_before_bonus=price_before_bonus,
        current_price=current_price,
        ingredients="durum wheat semolina, tomato",
        allergens=allergens or [],
        nutrition=[
            NutritionValue(
                code="ENER-",
                name="Energie",
                value=100,
                unit="kcal",
                basis_quantity=100,
                basis_unit="g",
            ),
            NutritionValue(
                code="PRO-",
                name="Eiwitten",
                value=4,
                unit="g",
                basis_quantity=100,
                basis_unit="g",
            ),
        ],
        discount_labels=[
            DiscountLabel.model_validate(
                {"code": "DISCOUNT_PERCENTAGE", "percentage": 25, "precisePercentage": 25}
            )
        ],
    )


def nutrition_payload(energy_kcal: float, protein_g: float) -> dict[str, float | None]:
    return {
        "energy_kcal": energy_kcal,
        "protein_g": protein_g,
        "carbs_g": None,
        "sugar_g": None,
        "fat_g": None,
        "saturated_fat_g": None,
        "fiber_g": None,
        "salt_g": None,
    }
