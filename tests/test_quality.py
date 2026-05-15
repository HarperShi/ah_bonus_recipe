from datetime import date, datetime, timezone

from ah_bonus_recipe.models import BonusProduct, BonusWeekDataset, DiscountLabel
from ah_bonus_recipe.quality import build_quality_report, product_issue_codes


def test_product_issue_codes_flags_missing_required_recipe_fields() -> None:
    product = BonusProduct(webshop_id=1, title="Incomplete")

    issues = product_issue_codes(product)

    assert "missing_price_before_bonus" in issues
    assert "missing_sales_unit_size" in issues
    assert "missing_ingredients" in issues
    assert "missing_allergens" in issues
    assert "missing_nutrition" in issues
    assert "missing_discount_labels" in issues


def test_build_quality_report_summarizes_fields_and_discount_support() -> None:
    dataset = BonusWeekDataset(
        week_start=date(2026, 5, 11),
        week_end=date(2026, 5, 17),
        scraped_at=datetime.now(timezone.utc),
        source_url="https://www.ah.nl/bonus",
        products=[
            BonusProduct(
                webshop_id=1,
                title="Complete",
                sales_unit_size="1 stuk",
                price_before_bonus=2.0,
                current_price=1.5,
                ingredients="Ingredienten: test.",
                allergens=[],
                nutrition=[],
                discount_labels=[
                    DiscountLabel.model_validate(
                        {"code": "DISCOUNT_PERCENTAGE", "percentage": 25}
                    )
                ],
            ),
            BonusProduct(webshop_id=2, title="Incomplete"),
        ],
        promotions=[],
    )

    report = build_quality_report(dataset, max_issue_products=1)

    assert report["product_count"] == 2
    assert report["field_coverage"]["price_before_bonus"]["present"] == 1
    assert report["discount_support"]["supported"] == 1
    assert report["discount_support"]["unsupported"] == 1
    assert report["products_with_issues_count"] == 2
    assert len(report["products_with_issues"]) == 1
