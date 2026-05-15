from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator


class DiscountCode(str, Enum):
    simple_price = "SIMPLE_PRICE"
    weight = "DISCOUNT_WEIGHT"
    x_for_y = "DISCOUNT_X_FOR_Y"
    percentage = "DISCOUNT_PERCENTAGE"
    tiered_percentage = "DISCOUNT_TIERED_PERCENT"
    bundle_bulk = "DISCOUNT_BUNDLE_BULK"
    second_half_price = "SECOND_HALF_PRICE"
    buy_n_pay_m = "BUY_N_PAY_M"
    unknown = "UNKNOWN"


class Image(BaseModel):
    url: str
    width: int | None = None
    height: int | None = None


class DiscountLabel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    default_description: str | None = Field(default=None, alias="defaultDescription")
    count: int | None = None
    price: float | None = None
    percentage: float | None = None
    unit: str | None = None
    free_count: int | None = Field(default=None, alias="freeCount")
    actual_count: int | None = Field(default=None, alias="actualCount")
    precise_percentage: float | None = Field(default=None, alias="precisePercentage")


class NutritionValue(BaseModel):
    code: str
    name: str
    value: float
    unit: str
    basis_quantity: float | None = None
    basis_unit: str | None = None


class AllergenStatus(BaseModel):
    code: str
    name: str
    containment: str


class BonusProduct(BaseModel):
    webshop_id: int
    title: str
    brand: str | None = None
    category: str | None = None
    sub_category: str | None = None
    url: HttpUrl | None = None
    sales_unit_size: str | None = None
    unit_price_description: str | None = None
    price_before_bonus: float | None = None
    current_price: float | None = None
    bonus_mechanism: str | None = None
    bonus_segment_id: str | int | None = None
    bonus_segment_description: str | None = None
    bonus_start_date: date | None = None
    bonus_end_date: date | None = None
    discount_labels: list[DiscountLabel] = Field(default_factory=list)
    images: list[Image] = Field(default_factory=list)
    ingredients: str | None = None
    description: str | None = None
    allergens: list[AllergenStatus] = Field(default_factory=list)
    nutrition: list[NutritionValue] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class BonusPromotion(BaseModel):
    id: str
    title: str
    category: str | None = None
    promotion_type: str | None = None
    bonus_start_date: date | None = None
    bonus_end_date: date | None = None
    discount_description: str | None = None
    discount_labels: list[DiscountLabel] = Field(default_factory=list)
    product_ids: list[int] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class BonusWeekDataset(BaseModel):
    week_start: date
    week_end: date
    scraped_at: datetime
    source_url: str
    promotions: list[BonusPromotion] = Field(default_factory=list)
    products: list[BonusProduct] = Field(default_factory=list)


class RecipePreferences(BaseModel):
    servings: int = Field(ge=1, le=20)
    allergies: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    cuisine: str | None = None
    main_ingredients: list[str] = Field(default_factory=list)
    diet: str | None = None
    max_cooking_minutes: int | None = Field(default=None, ge=5, le=240)
    skill_level: str | None = None
    budget: str | None = None
    meal_type: str | None = None
    spice_level: str | None = None
    equipment: list[str] = Field(default_factory=list)
    recipe_count: int = Field(default=3, ge=1, le=10)
    minimum_bonus_products: int = Field(default=2, ge=1, le=10)


class RecipeIngredient(BaseModel):
    name: str
    quantity: float = Field(ge=0)
    unit: str
    bonus_product_id: int | None = None
    packages_to_buy: int = Field(default=0, ge=0)

    @field_validator("packages_to_buy", mode="before")
    @classmethod
    def parse_display_package_count(cls, value: Any) -> Any:
        if value == "-":
            return 0
        return value

    @field_serializer("packages_to_buy")
    def serialize_package_count(self, value: int) -> int | str:
        if self.bonus_product_id is None and value == 0:
            return "-"
        return value


class RecipeNutritionEstimate(BaseModel):
    energy_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    sugar_g: float | None = None
    fat_g: float | None = None
    saturated_fat_g: float | None = None
    fiber_g: float | None = None
    salt_g: float | None = None


class GeneratedRecipe(BaseModel):
    title: str
    cuisine: str
    servings: int = Field(ge=1)
    total_time_minutes: int = Field(ge=1)
    bonus_product_ids: list[int] = Field(default_factory=list)
    ingredients: list[RecipeIngredient] = Field(default_factory=list)
    prep: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    estimated_nutrition_total: RecipeNutritionEstimate
    estimated_nutrition_per_serving: RecipeNutritionEstimate


class RecipeBonusProductUse(BaseModel):
    product_id: int
    title: str
    url: HttpUrl | None = None
    image_url: HttpUrl | None = None
    quantity: float
    unit: str
    packages_to_buy: int
    promotion_id: str | None = None
    promotion_title: str | None = None
    bonus_mechanism: str | None = None
    price_before_bonus: float | None = None
    current_price: float | None = None


class RecipeSavingsSummary(BaseModel):
    currency: str = "EUR"
    scope: str = "bonus_products_only"
    description: str = "Totals are for purchased AH Bonus products used by this recipe, not the whole meal."
    baseline_total: float = 0.0
    promo_total: float = 0.0
    savings: float = 0.0
    baseline_total_label: str = "Normal price for bonus products"
    promo_total_label: str = "Bonus price for bonus products"
    savings_label: str = "You save on bonus products"
    notes: list[str] = Field(default_factory=list)
    supported: bool = True
    unsupported_reasons: list[str] = Field(default_factory=list)


class RecipeNutritionReport(BaseModel):
    known_bonus_total: dict[str, float] = Field(default_factory=dict)
    known_bonus_per_serving: dict[str, float] = Field(default_factory=dict)
    estimated_total: RecipeNutritionEstimate
    estimated_per_serving: RecipeNutritionEstimate
    missing_bonus_nutrition_product_ids: list[int] = Field(default_factory=list)
    unconverted_bonus_nutrition_product_ids: list[int] = Field(default_factory=list)


class EnrichedRecipe(GeneratedRecipe):
    bonus_product_uses: list[RecipeBonusProductUse] = Field(default_factory=list)
    savings: RecipeSavingsSummary
    nutrition_report: RecipeNutritionReport
    validation_warnings: list[str] = Field(default_factory=list)


class RecipeGenerationResult(BaseModel):
    week_start: date
    week_end: date
    preferences: RecipePreferences
    candidate_product_count: int
    recipes: list[EnrichedRecipe] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
