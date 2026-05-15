from __future__ import annotations

import re
from dataclasses import dataclass, field

from ah_bonus_recipe.models import BonusProduct, GeneratedRecipe, NutritionValue, RecipeIngredient


NUTRIENT_NAME_MAP = {
    "eiwitten": "protein_g",
    "koolhydraten": "carbs_g",
    "waarvan suikers": "sugar_g",
    "vet": "fat_g",
    "waarvan verzadigd": "saturated_fat_g",
    "voedingsvezel": "fiber_g",
    "zout": "salt_g",
}

MASS_UNITS = {
    "g": ("g", 1.0),
    "gram": ("g", 1.0),
    "grams": ("g", 1.0),
    "kg": ("g", 1000.0),
    "kilogram": ("g", 1000.0),
}

VOLUME_UNITS = {
    "ml": ("ml", 1.0),
    "milliliter": ("ml", 1.0),
    "l": ("ml", 1000.0),
    "liter": ("ml", 1000.0),
}

PACK_UNITS = {
    "pack",
    "package",
    "packet",
    "pak",
    "verpakking",
    "bottle",
    "fles",
    "jar",
    "pot",
    "can",
    "blik",
}


@dataclass
class KnownNutritionCalculation:
    totals: dict[str, float] = field(default_factory=dict)
    missing_product_ids: set[int] = field(default_factory=set)
    unconverted_product_ids: set[int] = field(default_factory=set)


def calculate_known_bonus_nutrition(
    recipe: GeneratedRecipe,
    products_by_id: dict[int, BonusProduct],
) -> KnownNutritionCalculation:
    """Calculate nutrition from AH data for bonus ingredients with convertible units."""

    calculation = KnownNutritionCalculation()
    for ingredient in recipe.ingredients:
        if ingredient.bonus_product_id is None:
            continue
        product = products_by_id.get(ingredient.bonus_product_id)
        if product is None:
            calculation.missing_product_ids.add(ingredient.bonus_product_id)
            continue
        if not product.nutrition:
            calculation.missing_product_ids.add(product.webshop_id)
            continue

        converted_any = False
        for nutrient in product.nutrition:
            key = nutrient_key(nutrient)
            if key is None or nutrient.basis_quantity is None or nutrient.basis_unit is None:
                continue
            basis_amount = ingredient_amount_in_basis_unit(ingredient, product, nutrient.basis_unit)
            if basis_amount is None:
                continue
            converted_value = convert_nutrient_value(nutrient.value, nutrient.unit, key)
            if converted_value is None:
                continue
            multiplier = basis_amount / nutrient.basis_quantity
            calculation.totals[key] = calculation.totals.get(key, 0.0) + converted_value * multiplier
            converted_any = True

        if not converted_any:
            calculation.unconverted_product_ids.add(product.webshop_id)

    calculation.totals = {key: round(value, 1) for key, value in sorted(calculation.totals.items())}
    return calculation


def per_serving(totals: dict[str, float], servings: int) -> dict[str, float]:
    if servings <= 0:
        return {}
    return {key: round(value / servings, 1) for key, value in totals.items()}


def nutrient_key(nutrient: NutritionValue) -> str | None:
    name = nutrient.name.strip().lower()
    unit = nutrient.unit.strip().lower()
    if name == "energie" and unit == "kcal":
        return "energy_kcal"
    return NUTRIENT_NAME_MAP.get(name)


def convert_nutrient_value(value: float, unit: str, key: str) -> float | None:
    normalized_unit = unit.strip().lower()
    if key == "energy_kcal":
        return value if normalized_unit == "kcal" else None
    if not key.endswith("_g"):
        return value
    if normalized_unit == "g":
        return value
    if normalized_unit == "mg":
        return value / 1000
    if normalized_unit in {"µg", "ug"}:
        return value / 1_000_000
    return None


def ingredient_amount_in_basis_unit(
    ingredient: RecipeIngredient,
    product: BonusProduct,
    basis_unit: str,
) -> float | None:
    normalized_basis = normalize_basis_unit(basis_unit)
    if normalized_basis is None:
        return None

    quantity = ingredient.quantity
    unit = ingredient.unit.strip().lower()
    direct = normalize_amount(quantity, unit)
    if direct and direct[1] == normalized_basis:
        return direct[0]

    if unit in PACK_UNITS or unit.endswith("(s)"):
        pack_size = parse_sales_unit_size(product.sales_unit_size)
        if pack_size and pack_size[1] == normalized_basis:
            return quantity * pack_size[0]

    return None


def normalize_basis_unit(unit: str) -> str | None:
    normalized = unit.strip().lower()
    if normalized in MASS_UNITS:
        return "g"
    if normalized in VOLUME_UNITS:
        return "ml"
    return None


def normalize_amount(quantity: float, unit: str) -> tuple[float, str] | None:
    normalized = unit.strip().lower()
    if normalized in MASS_UNITS:
        basis_unit, multiplier = MASS_UNITS[normalized]
        return quantity * multiplier, basis_unit
    if normalized in VOLUME_UNITS:
        basis_unit, multiplier = VOLUME_UNITS[normalized]
        return quantity * multiplier, basis_unit
    return None


def parse_sales_unit_size(sales_unit_size: str | None) -> tuple[float, str] | None:
    """Parse common AH sizes like '400 g', '0,75 l', or '6 x 0,33 l'."""

    if not sales_unit_size:
        return None
    text = sales_unit_size.strip().lower().replace(",", ".")
    match = re.search(
        r"(?:(?P<count>\d+(?:\.\d+)?)\s*x\s*)?(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>kg|g|l|ml)\b",
        text,
    )
    if not match:
        return None

    count = float(match.group("count") or 1)
    amount = float(match.group("amount"))
    unit = match.group("unit")
    normalized = normalize_amount(count * amount, unit)
    if normalized is None:
        return None
    return normalized
