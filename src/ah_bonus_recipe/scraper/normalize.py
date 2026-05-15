from __future__ import annotations

from typing import Any

from ah_bonus_recipe.models import AllergenStatus, BonusProduct, DiscountLabel, Image, NutritionValue


def normalize_product_detail(detail: dict[str, Any]) -> BonusProduct:
    product_card = detail["productCard"]
    trade_item = detail.get("tradeItem", {})
    return BonusProduct(
        webshop_id=int(product_card["webshopId"]),
        title=product_card["title"],
        brand=product_card.get("brand"),
        category=product_card.get("mainCategory"),
        sub_category=product_card.get("subCategory"),
        url=f"https://www.ah.nl/producten/product/wi{product_card['webshopId']}",
        sales_unit_size=product_card.get("salesUnitSize"),
        unit_price_description=product_card.get("unitPriceDescription"),
        price_before_bonus=product_card.get("priceBeforeBonus"),
        current_price=product_card.get("currentPrice"),
        bonus_mechanism=product_card.get("bonusMechanism"),
        bonus_segment_id=product_card.get("bonusSegmentId"),
        bonus_segment_description=product_card.get("bonusSegmentDescription"),
        bonus_start_date=product_card.get("bonusStartDate"),
        bonus_end_date=product_card.get("bonusEndDate"),
        discount_labels=[DiscountLabel.model_validate(x) for x in product_card.get("discountLabels", [])],
        images=[Image.model_validate(x) for x in product_card.get("images", [])],
        ingredients=trade_item.get("foodAndBeverageIngredientStatement"),
        description=extract_description(product_card, trade_item),
        allergens=extract_allergens(trade_item),
        nutrition=extract_nutrition(trade_item),
        raw=detail,
    )


def extract_description(product_card: dict[str, Any], trade_item: dict[str, Any]) -> str | None:
    marketing = trade_item.get("marketingInformationModule", {})
    return (
        marketing.get("tradeItemMarketingMessage")
        or product_card.get("descriptionFull")
        or product_card.get("descriptionHighlights")
    )


def extract_allergens(trade_item: dict[str, Any]) -> list[AllergenStatus]:
    allergens: list[AllergenStatus] = []
    for block in trade_item.get("allergenInformation", []):
        for item in block.get("items", []):
            type_code = item.get("typeCode", {})
            containment = item.get("levelOfContainmentCode", {})
            if type_code:
                allergens.append(
                    AllergenStatus(
                        code=type_code.get("value", ""),
                        name=type_code.get("label", ""),
                        containment=containment.get("value") or containment.get("label", ""),
                    )
                )
    return allergens


def extract_nutrition(trade_item: dict[str, Any]) -> list[NutritionValue]:
    nutrition_values: list[NutritionValue] = []
    nutritional_info = trade_item.get("nutritionalInformation", {})
    for header in nutritional_info.get("nutrientHeaders", []):
        basis = header.get("nutrientBasisQuantity", {})
        basis_unit = basis.get("measurementUnitCode", {})
        for detail in header.get("nutrientDetail", []):
            nutrient_type = detail.get("nutrientTypeCode", {})
            quantities = detail.get("quantityContained", [])
            for quantity in quantities:
                unit = quantity.get("measurementUnitCode", {})
                value = quantity.get("value")
                if value is None:
                    continue
                nutrition_values.append(
                    NutritionValue(
                        code=nutrient_type.get("value", ""),
                        name=nutrient_type.get("label", ""),
                        value=float(value),
                        unit=unit.get("value") or unit.get("label", ""),
                        basis_quantity=basis.get("value"),
                        basis_unit=basis_unit.get("value") or basis_unit.get("label"),
                    )
                )
    return nutrition_values
