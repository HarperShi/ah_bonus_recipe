from ah_bonus_recipe.pricing import (
    CartLine,
    buy_n_pay_m,
    estimate_product_savings,
    estimate_promotion_savings,
    percentage_off,
    second_half_price,
    tiered_percentage_off,
    weight_discount,
    x_for_y,
)
from ah_bonus_recipe.models import BonusProduct, BonusPromotion, DiscountLabel


def test_x_for_y_bundle_savings() -> None:
    result = x_for_y([CartLine(1, 1.69, 2)], count=2, bundle_price=2.49)
    assert result.baseline_total == 3.38
    assert result.promo_total == 2.49
    assert result.savings == 0.89


def test_x_for_y_keeps_remainder_at_normal_price() -> None:
    result = x_for_y([CartLine(1, 1.69, 3)], count=2, bundle_price=2.49)
    assert result.baseline_total == 5.07
    assert result.promo_total == 4.18


def test_percentage_off() -> None:
    result = percentage_off([CartLine(1, 10.0, 1)], percentage=25)
    assert result.promo_total == 7.5
    assert result.savings == 2.5


def test_tiered_percentage_off() -> None:
    result = tiered_percentage_off([CartLine(1, 2.0, 2)], tiers={1: 30, 2: 50})
    assert result.baseline_total == 4.0
    assert result.promo_total == 2.0


def test_buy_n_pay_m_uses_cheapest_as_free_item() -> None:
    result = buy_n_pay_m([CartLine(1, 3.0), CartLine(2, 2.0)], buy_quantity=2, pay_quantity=1)
    assert result.baseline_total == 5.0
    assert result.promo_total == 3.0


def test_second_half_price_discounts_cheapest_in_pair() -> None:
    result = second_half_price([CartLine(1, 3.0), CartLine(2, 2.0)])
    assert result.baseline_total == 5.0
    assert result.promo_total == 4.0


def test_weight_discount() -> None:
    result = weight_discount(
        grams_used=500,
        normal_price_per_kg=2.98,
        promo_count=500,
        promo_unit="GRAM",
        promo_price=1.09,
    )
    assert result.baseline_total == 1.49
    assert result.promo_total == 1.09


def test_estimate_product_savings_for_x_plus_y_free() -> None:
    product = bonus_product(
        labels=[{"code": "DISCOUNT_X_PLUS_Y_FREE", "count": 1, "free_count": 1}],
        price_before_bonus=3.0,
    )

    result = estimate_product_savings(product, quantity=2)

    assert result.supported is True
    assert result.baseline_total == 6.0
    assert result.promo_total == 3.0
    assert result.savings == 3.0


def test_estimate_product_savings_for_fixed_price() -> None:
    product = bonus_product(
        labels=[{"code": "DISCOUNT_FIXED_PRICE", "price": 0.99}],
        price_before_bonus=1.99,
    )

    result = estimate_product_savings(product, quantity=3)

    assert result.supported is True
    assert result.baseline_total == 5.97
    assert result.promo_total == 2.97


def test_estimate_product_savings_uses_current_price_when_label_has_no_fields() -> None:
    product = bonus_product(
        labels=[{"code": "DISCOUNT_BONUS"}],
        price_before_bonus=5.99,
        current_price=4.99,
    )

    result = estimate_product_savings(product)

    assert result.supported is True
    assert result.savings == 1.0


def test_estimate_product_savings_reports_missing_current_price() -> None:
    product = bonus_product(labels=[{"code": "DISCOUNT_BONUS"}], price_before_bonus=5.99)

    result = estimate_product_savings(product)

    assert result.supported is False
    assert result.reason == "missing_current_price"


def test_estimate_promotion_savings_uses_group_labels() -> None:
    products = {
        1: bonus_product(webshop_id=1, price_before_bonus=3.0),
        2: bonus_product(webshop_id=2, price_before_bonus=2.0),
    }
    promotion = BonusPromotion(
        id="promo",
        title="2 voor 4",
        discount_labels=[
            DiscountLabel.model_validate({"code": "DISCOUNT_X_FOR_Y", "count": 2, "price": 4.0})
        ],
        product_ids=[1, 2],
    )

    result = estimate_promotion_savings(promotion, {1: 1, 2: 1}, products)

    assert result.supported is True
    assert result.baseline_total == 5.0
    assert result.promo_total == 4.0


def bonus_product(
    *,
    webshop_id: int = 1,
    labels: list[dict] | None = None,
    price_before_bonus: float | None = 2.0,
    current_price: float | None = None,
) -> BonusProduct:
    return BonusProduct(
        webshop_id=webshop_id,
        title=f"Product {webshop_id}",
        price_before_bonus=price_before_bonus,
        current_price=current_price,
        discount_labels=[DiscountLabel.model_validate(label) for label in labels or []],
    )
