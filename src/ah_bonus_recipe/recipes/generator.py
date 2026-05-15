from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI
from pydantic import ValidationError

from ah_bonus_recipe.config import PROCESSED_DATA_DIR
from ah_bonus_recipe.models import (
    BonusProduct,
    BonusPromotion,
    BonusWeekDataset,
    EnrichedRecipe,
    GeneratedRecipe,
    RecipeBonusProductUse,
    RecipeGenerationResult,
    RecipeNutritionReport,
    RecipePreferences,
    RecipeSavingsSummary,
)
from ah_bonus_recipe.pricing import DiscountEstimate, estimate_product_savings, estimate_promotion_savings
from ah_bonus_recipe.recipes.nutrition import calculate_known_bonus_nutrition, per_serving


DEFAULT_DATASET_PATH = PROCESSED_DATA_DIR / "latest_bonus_week.json"
DEFAULT_RECIPE_OUTPUT_PATH = PROCESSED_DATA_DIR / "latest_recipes.json"
DEFAULT_CANDIDATE_LIMIT = 90

RECIPE_NUTRITION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "energy_kcal": {"type": ["number", "null"]},
        "protein_g": {"type": ["number", "null"]},
        "carbs_g": {"type": ["number", "null"]},
        "sugar_g": {"type": ["number", "null"]},
        "fat_g": {"type": ["number", "null"]},
        "saturated_fat_g": {"type": ["number", "null"]},
        "fiber_g": {"type": ["number", "null"]},
        "salt_g": {"type": ["number", "null"]},
    },
    "required": [
        "energy_kcal",
        "protein_g",
        "carbs_g",
        "sugar_g",
        "fat_g",
        "saturated_fat_g",
        "fiber_g",
        "salt_g",
    ],
}

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
                        "total_time_minutes": {"type": "integer"},
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
                                    "packages_to_buy": {"type": "integer"},
                                },
                                "required": [
                                    "name",
                                    "quantity",
                                    "unit",
                                    "bonus_product_id",
                                    "packages_to_buy",
                                ],
                            },
                        },
                        "prep": {"type": "array", "items": {"type": "string"}},
                        "steps": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": "array", "items": {"type": "string"}},
                        "estimated_nutrition_total": RECIPE_NUTRITION_SCHEMA,
                        "estimated_nutrition_per_serving": RECIPE_NUTRITION_SCHEMA,
                    },
                    "required": [
                        "title",
                        "cuisine",
                        "servings",
                        "total_time_minutes",
                        "bonus_product_ids",
                        "ingredients",
                        "prep",
                        "steps",
                        "notes",
                        "estimated_nutrition_total",
                        "estimated_nutrition_per_serving",
                    ],
                },
            }
        },
        "required": ["recipes"],
    },
    "strict": True,
}

NON_RECIPE_CATEGORIES = {
    "Baby en kind",
    "Bier, wijn, aperitieven",
    "Drogisterij",
    "Frisdrank, sappen, water",
    "Gezondheid en sport",
    "Huishouden",
    "Koffie, thee",
    "Koken, tafelen, vrije tijd",
}

ALLERGEN_ALIASES = {
    "gluten": ["gluten", "tarwe", "gerst", "rogge", "haver", "spelt"],
    "lactose": ["lactose", "melk"],
    "milk": ["melk", "lactose"],
    "dairy": ["melk", "lactose"],
    "egg": ["ei", "eieren"],
    "eggs": ["ei", "eieren"],
    "fish": ["vis"],
    "shellfish": ["schaaldieren", "weekdieren", "garnaal", "garnalen", "krab"],
    "nuts": [
        "noten",
        "amandel",
        "hazelnoot",
        "walnoot",
        "cashew",
        "pistache",
        "pecan",
        "macadamia",
        "paranoot",
    ],
    "peanuts": ["pinda"],
    "peanut": ["pinda"],
    "soy": ["soja"],
    "mustard": ["mosterd"],
    "celery": ["selderij"],
    "sesame": ["sesam"],
    "sulfites": ["sulfiet"],
    "sulphites": ["sulfiet"],
}

MEAT_AND_FISH_TERMS = {
    "bacon",
    "gehakt",
    "garnalen",
    "ham",
    "kip",
    "krab",
    "rund",
    "spek",
    "vis",
    "vlees",
    "varken",
    "worst",
    "zalm",
}

ANIMAL_PRODUCT_TERMS = MEAT_AND_FISH_TERMS | {
    "boter",
    "ei",
    "eieren",
    "kaas",
    "lactose",
    "melk",
    "room",
    "yoghurt",
    "yogurt",
    "zuivel",
}

PORK_AND_ALCOHOL_TERMS = {"varken", "spek", "bacon", "ham", "salami", "wijn", "bier", "alcohol"}


class RecipeGenerationError(RuntimeError):
    """Raised when recipe generation cannot produce a usable result."""


class OpenAICompatibleClient(Protocol):
    responses: Any


def generate_recipe_plan(
    preferences: RecipePreferences,
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_path: Path | None = None,
    model: str | None = None,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    client: OpenAICompatibleClient | None = None,
) -> RecipeGenerationResult:
    """Load the weekly dataset, generate recipe candidates, and enrich them locally."""

    dataset = load_bonus_week_dataset(dataset_path)
    candidate_products = select_candidate_products(
        dataset.products,
        preferences,
        limit=candidate_limit,
    )
    if len(candidate_products) < preferences.minimum_bonus_products:
        raise RecipeGenerationError(
            "Not enough usable bonus products after allergy/diet/preference filtering. "
            f"Need at least {preferences.minimum_bonus_products}, found {len(candidate_products)}."
        )

    generated_recipes = generate_recipe_candidates(
        preferences,
        candidate_products,
        model=model,
        client=client,
    )
    result = enrich_generated_recipes(
        generated_recipes,
        dataset,
        preferences,
        candidate_product_count=len(candidate_products),
    )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return result


def load_bonus_week_dataset(path: Path = DEFAULT_DATASET_PATH) -> BonusWeekDataset:
    if not path.exists():
        raise FileNotFoundError(f"Bonus week dataset not found: {path}")
    return BonusWeekDataset.model_validate_json(path.read_text(encoding="utf-8"))


def generate_recipe_candidates(
    preferences: RecipePreferences,
    bonus_products: list[BonusProduct],
    *,
    model: str | None = None,
    client: OpenAICompatibleClient | None = None,
) -> list[GeneratedRecipe]:
    """Ask OpenAI for structured recipe candidates from a filtered bonus product subset."""

    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RecipeGenerationError("OPENAI_API_KEY is required to generate recipes.")
        client = OpenAI()
    model = model or os.getenv("OPENAI_RECIPE_MODEL", "gpt-5.4-mini")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": recipe_system_prompt(preferences),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "preferences": preferences.model_dump(),
                        "bonus_products": [
                            product_prompt_payload(product) for product in bonus_products
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        text={"format": {"type": "json_schema", **RECIPE_JSON_SCHEMA}},
    )
    try:
        payload = json.loads(response.output_text)
        recipes = [GeneratedRecipe.model_validate(item) for item in payload["recipes"]]
    except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as exc:
        raise RecipeGenerationError(f"OpenAI returned an invalid recipe payload: {exc}") from exc

    return recipes


def recipe_system_prompt(preferences: RecipePreferences) -> str:
    return (
        "You generate practical home-cooking recipes for Albert Heijn weekly Bonus products. "
        "Return only JSON matching the schema. Write recipe text in English while preserving "
        "Dutch product names when used as ingredient names. Use only the provided webshop_id "
        "values for bonus_product_id and bonus_product_ids; never invent product IDs. "
        f"Create {preferences.recipe_count} recipes for {preferences.servings} people. "
        "Each recipe must use at least "
        f"{preferences.minimum_bonus_products} distinct bonus products. "
        "Bonus products may be combined with pantry or non-bonus ingredients. "
        "For every bonus ingredient line, set bonus_product_id to the AH webshop_id and "
        "packages_to_buy to the whole number of packs that should be bought for the recipe; "
        "for non-bonus ingredients, set bonus_product_id to null and packages_to_buy to 0. "
        "Avoid all stated allergies, disliked ingredients, and diet conflicts. "
        "Estimate total and per-serving nutrition for the whole recipe using common food "
        "knowledge for ingredients that are not in the AH dataset."
    )


def product_prompt_payload(product: BonusProduct) -> dict[str, Any]:
    return {
        "webshop_id": product.webshop_id,
        "title": product.title,
        "brand": product.brand,
        "category": product.category,
        "sub_category": product.sub_category,
        "sales_unit_size": product.sales_unit_size,
        "unit_price_description": product.unit_price_description,
        "price_before_bonus": product.price_before_bonus,
        "current_price": product.current_price,
        "bonus_mechanism": product.bonus_mechanism,
        "bonus_segment_description": product.bonus_segment_description,
        "discount_labels": [
            label.model_dump(exclude_none=True) for label in product.discount_labels[:3]
        ],
        "allergens": [
            {"name": allergen.name, "containment": allergen.containment}
            for allergen in product.allergens
            if allergen.containment != "FREE_FROM"
        ],
        "ingredients": truncate(product.ingredients, 380),
        "nutrition": nutrition_prompt_payload(product),
        "url": str(product.url) if product.url else None,
    }


def nutrition_prompt_payload(product: BonusProduct) -> list[dict[str, Any]]:
    selected_names = {
        "Energie",
        "Eiwitten",
        "Koolhydraten",
        "waarvan suikers",
        "Vet",
        "waarvan verzadigd",
        "Voedingsvezel",
        "Zout",
    }
    return [
        nutrient.model_dump(exclude_none=True)
        for nutrient in product.nutrition
        if nutrient.name in selected_names
    ][:12]


def select_candidate_products(
    products: list[BonusProduct],
    preferences: RecipePreferences,
    *,
    limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> list[BonusProduct]:
    scored = []
    for product in products:
        if not is_recipe_product(product):
            continue
        if conflicts_with_preferences(product, preferences):
            continue
        scored.append((score_product(product, preferences), product.webshop_id, product))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [product for _, _, product in scored[:limit]]


def is_recipe_product(product: BonusProduct) -> bool:
    if product.category in NON_RECIPE_CATEGORIES:
        return False
    if not (product.ingredients or product.nutrition):
        return False
    text = product_text(product)
    blocked_terms = {
        "shampoo",
        "conditioner",
        "deodorant",
        "tandpasta",
        "wasmiddel",
        "luiers",
        "servetten",
    }
    return not any(term in text for term in blocked_terms)


def conflicts_with_preferences(product: BonusProduct, preferences: RecipePreferences) -> bool:
    text = product_text(product)
    if allergy_conflict(product, preferences.allergies):
        return True
    if any(term.strip().lower() and term.strip().lower() in text for term in preferences.disliked_ingredients):
        return True

    diet = (preferences.diet or "").strip().lower()
    if diet == "vegetarian" and contains_any_term(text, MEAT_AND_FISH_TERMS):
        return True
    if diet == "vegan" and contains_any_term(text, ANIMAL_PRODUCT_TERMS):
        return True
    if diet == "halal" and contains_any_term(text, PORK_AND_ALCOHOL_TERMS):
        return True
    return False


def allergy_conflict(product: BonusProduct, allergies: list[str]) -> bool:
    if not allergies:
        return False
    allergy_terms = []
    for allergy in allergies:
        normalized = allergy.strip().lower()
        allergy_terms.extend(ALLERGEN_ALIASES.get(normalized, [normalized]))
    if not allergy_terms:
        return False

    for allergen in product.allergens:
        if allergen.containment == "FREE_FROM":
            continue
        allergen_text = f"{allergen.code} {allergen.name}".lower()
        if any(term in allergen_text for term in allergy_terms):
            return True

    ingredients = (product.ingredients or "").lower()
    return any(term in ingredients for term in allergy_terms)


def score_product(product: BonusProduct, preferences: RecipePreferences) -> float:
    score = 0.0
    if product.ingredients:
        score += 3
    if product.nutrition:
        score += 3
    if product.price_before_bonus is not None and product.current_price is not None:
        score += 2
    if product.sales_unit_size:
        score += 1
    if product.category in {"Groente, aardappelen", "Vis", "Vlees, kip", "Vega", "Zuivel, eieren"}:
        score += 3
    if product.category in {"Koek, snoep, chocolade", "Borrel, chips, snacks"}:
        score -= 2

    text = product_text(product)
    for ingredient in preferences.main_ingredients:
        term = ingredient.strip().lower()
        if term and term in text:
            score += 12

    if preferences.meal_type in {"dinner", "lunch"} and product.category == "Maaltijden, salades":
        score += 2
    if preferences.diet == "high protein" and (
        product.category in {"Vis", "Vlees, kip", "Vega", "Zuivel, eieren"} or "eiwit" in text
    ):
        score += 4

    if product.price_before_bonus and product.current_price:
        score += min(5, max(0, product.price_before_bonus - product.current_price))
    return score


def enrich_generated_recipes(
    generated_recipes: list[GeneratedRecipe],
    dataset: BonusWeekDataset,
    preferences: RecipePreferences,
    *,
    candidate_product_count: int,
) -> RecipeGenerationResult:
    products_by_id = {product.webshop_id: product for product in dataset.products}
    promotion_by_product = build_promotion_by_product(dataset.promotions)
    enriched_recipes = []
    warnings = []

    for recipe in generated_recipes:
        validation_warnings = validate_generated_recipe(recipe, products_by_id, preferences)
        bonus_quantities = recipe_bonus_pack_quantities(recipe)
        bonus_product_uses = build_bonus_product_uses(
            recipe,
            products_by_id,
            promotion_by_product,
        )
        savings = calculate_recipe_savings(
            bonus_quantities,
            products_by_id,
            promotion_by_product,
        )
        nutrition = build_nutrition_report(recipe, products_by_id)
        enriched_recipes.append(
            EnrichedRecipe(
                **recipe.model_dump(),
                bonus_product_uses=bonus_product_uses,
                savings=savings,
                nutrition_report=nutrition,
                validation_warnings=validation_warnings,
            )
        )

    if len(enriched_recipes) < preferences.recipe_count:
        warnings.append(
            f"OpenAI returned {len(enriched_recipes)} recipes; requested {preferences.recipe_count}."
        )

    invalid_count = sum(1 for recipe in enriched_recipes if recipe.validation_warnings)
    if invalid_count:
        warnings.append(f"{invalid_count} recipe(s) have validation warnings.")

    return RecipeGenerationResult(
        week_start=dataset.week_start,
        week_end=dataset.week_end,
        preferences=preferences,
        candidate_product_count=candidate_product_count,
        recipes=enriched_recipes,
        warnings=warnings,
    )


def validate_generated_recipe(
    recipe: GeneratedRecipe,
    products_by_id: dict[int, BonusProduct],
    preferences: RecipePreferences,
) -> list[str]:
    warnings = []
    ingredient_bonus_ids = {
        ingredient.bonus_product_id
        for ingredient in recipe.ingredients
        if ingredient.bonus_product_id is not None
    }
    declared_bonus_ids = set(recipe.bonus_product_ids)
    all_bonus_ids = ingredient_bonus_ids | declared_bonus_ids
    unknown_ids = sorted(product_id for product_id in all_bonus_ids if product_id not in products_by_id)
    if unknown_ids:
        warnings.append(f"Unknown bonus product IDs: {unknown_ids}")
    known_bonus_ids = {product_id for product_id in all_bonus_ids if product_id in products_by_id}
    if len(known_bonus_ids) < preferences.minimum_bonus_products:
        warnings.append(
            "Recipe uses "
            f"{len(known_bonus_ids)} known bonus products; "
            f"minimum is {preferences.minimum_bonus_products}."
        )
    if recipe.servings != preferences.servings:
        warnings.append(f"Recipe servings {recipe.servings} differs from requested {preferences.servings}.")

    for product_id in known_bonus_ids:
        product = products_by_id[product_id]
        if allergy_conflict(product, preferences.allergies):
            warnings.append(f"Bonus product {product_id} conflicts with allergy preferences.")
    return warnings


def build_promotion_by_product(promotions: list[BonusPromotion]) -> dict[int, BonusPromotion]:
    promotion_by_product = {}
    for promotion in promotions:
        for product_id in promotion.product_ids:
            promotion_by_product.setdefault(product_id, promotion)
    return promotion_by_product


def recipe_bonus_pack_quantities(recipe: GeneratedRecipe) -> dict[int, int]:
    quantities: dict[int, int] = defaultdict(int)
    for ingredient in recipe.ingredients:
        if ingredient.bonus_product_id is None:
            continue
        quantities[ingredient.bonus_product_id] += max(1, ingredient.packages_to_buy)
    return dict(quantities)


def build_bonus_product_uses(
    recipe: GeneratedRecipe,
    products_by_id: dict[int, BonusProduct],
    promotion_by_product: dict[int, BonusPromotion],
) -> list[RecipeBonusProductUse]:
    uses = []
    for ingredient in recipe.ingredients:
        if ingredient.bonus_product_id is None:
            continue
        product = products_by_id.get(ingredient.bonus_product_id)
        if product is None:
            continue
        promotion = promotion_by_product.get(product.webshop_id)
        uses.append(
            RecipeBonusProductUse(
                product_id=product.webshop_id,
                title=product.title,
                url=product.url,
                image_url=preferred_product_image_url(product),
                quantity=ingredient.quantity,
                unit=ingredient.unit,
                packages_to_buy=max(1, ingredient.packages_to_buy),
                promotion_id=promotion.id if promotion else None,
                promotion_title=promotion.title if promotion else None,
                bonus_mechanism=product.bonus_mechanism,
                price_before_bonus=product.price_before_bonus,
                current_price=product.current_price,
            )
        )
    return uses


def calculate_recipe_savings(
    product_quantities: dict[int, int],
    products_by_id: dict[int, BonusProduct],
    promotion_by_product: dict[int, BonusPromotion],
) -> RecipeSavingsSummary:
    estimates = []
    grouped_quantities: dict[str, dict[int, int]] = defaultdict(dict)
    promotions_by_id: dict[str, BonusPromotion] = {}

    for product_id, quantity in product_quantities.items():
        promotion = promotion_by_product.get(product_id)
        if promotion is None:
            product = products_by_id.get(product_id)
            if product is None:
                estimates.append(
                    DiscountEstimate.unsupported(
                        discount_code=None,
                        reason=f"unknown_product:{product_id}",
                    )
                )
                continue
            estimates.append(estimate_product_savings(product, quantity=quantity))
            continue
        promotions_by_id[promotion.id] = promotion
        grouped_quantities[promotion.id][product_id] = quantity

    for promotion_id, quantities in grouped_quantities.items():
        promotion = promotions_by_id[promotion_id]
        estimate = estimate_promotion_savings(promotion, quantities, products_by_id)
        if not estimate.supported:
            product_estimates = [
                estimate_product_savings(products_by_id[product_id], quantity=quantity)
                for product_id, quantity in quantities.items()
                if product_id in products_by_id
            ]
            if product_estimates and all(item.supported for item in product_estimates):
                estimates.extend(product_estimates)
            else:
                estimates.append(estimate)
        else:
            estimates.append(estimate)

    baseline_total = round(sum(estimate.baseline_total for estimate in estimates), 2)
    promo_total = round(sum(estimate.promo_total for estimate in estimates), 2)
    unsupported_reasons = [
        f"{estimate.discount_code or 'UNKNOWN'}:{estimate.reason}"
        for estimate in estimates
        if not estimate.supported and estimate.reason
    ]
    notes = unique_notes(note for estimate in estimates for note in estimate.notes)
    return RecipeSavingsSummary(
        baseline_total=baseline_total,
        promo_total=promo_total,
        savings=round(baseline_total - promo_total, 2),
        notes=notes,
        supported=not unsupported_reasons,
        unsupported_reasons=unsupported_reasons,
    )


def build_nutrition_report(
    recipe: GeneratedRecipe,
    products_by_id: dict[int, BonusProduct],
) -> RecipeNutritionReport:
    known = calculate_known_bonus_nutrition(recipe, products_by_id)
    return RecipeNutritionReport(
        known_bonus_total=known.totals,
        known_bonus_per_serving=per_serving(known.totals, recipe.servings),
        estimated_total=recipe.estimated_nutrition_total,
        estimated_per_serving=recipe.estimated_nutrition_per_serving,
        missing_bonus_nutrition_product_ids=sorted(known.missing_product_ids),
        unconverted_bonus_nutrition_product_ids=sorted(known.unconverted_product_ids),
    )


def product_text(product: BonusProduct) -> str:
    return " ".join(
        item
        for item in [
            product.title,
            product.brand,
            product.category,
            product.sub_category,
            product.ingredients,
            product.description,
        ]
        if item
    ).lower()


def preferred_product_image_url(product: BonusProduct) -> str | None:
    if not product.images:
        return None
    smaller_images = [image for image in product.images if image.width and image.width <= 400]
    image = smaller_images[0] if smaller_images else product.images[0]
    return image.url


def contains_any_term(text: str, terms: set[str]) -> bool:
    return any(contains_term(text, term) for term in terms)


def contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term.lower())
    if len(term) <= 3:
        return re.search(rf"(?<!\w){escaped}(?!\w)", text) is not None
    return term.lower() in text


def unique_notes(notes: Any) -> list[str]:
    unique = []
    seen = set()
    for note in notes:
        if not note or note in seen:
            continue
        unique.append(note)
        seen.add(note)
    return unique


def truncate(value: str | None, max_chars: int) -> str | None:
    if value is None or len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "..."
