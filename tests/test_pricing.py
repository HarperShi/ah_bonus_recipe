from ah_bonus_recipe.pricing import (
    CartLine,
    buy_n_pay_m,
    percentage_off,
    second_half_price,
    tiered_percentage_off,
    weight_discount,
    x_for_y,
)


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
