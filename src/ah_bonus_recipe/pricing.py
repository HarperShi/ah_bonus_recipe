from __future__ import annotations

import re
from dataclasses import dataclass
from math import floor

from ah_bonus_recipe.models import BonusProduct, BonusPromotion, DiscountLabel


SUPPORTED_DISCOUNT_CODES = {
    "DISCOUNT_AMOUNT",
    "DISCOUNT_BONUS",
    "DISCOUNT_BUNDLE_BULK",
    "DISCOUNT_FIXED_PRICE",
    "DISCOUNT_ONE_HALF_PRICE",
    "DISCOUNT_OP_IS_OP",
    "DISCOUNT_PERCENTAGE",
    "DISCOUNT_TIERED_PERCENT",
    "DISCOUNT_WEIGHT",
    "DISCOUNT_X_FOR_Y",
    "DISCOUNT_X_PLUS_Y_FREE",
}


@dataclass(frozen=True)
class CartLine:
    product_id: int
    normal_price: float
    quantity: int = 1


@dataclass(frozen=True)
class SavingsResult:
    baseline_total: float
    promo_total: float

    @property
    def savings(self) -> float:
        return round(self.baseline_total - self.promo_total, 2)


@dataclass(frozen=True)
class DiscountEstimate:
    supported: bool
    discount_code: str | None
    baseline_total: float
    promo_total: float
    savings: float
    reason: str | None = None
    notes: tuple[str, ...] = ()

    @classmethod
    def unsupported(
        cls,
        *,
        discount_code: str | None,
        reason: str,
        baseline_total: float = 0.0,
    ) -> "DiscountEstimate":
        return cls(
            supported=False,
            discount_code=discount_code,
            baseline_total=round(baseline_total, 2),
            promo_total=round(baseline_total, 2),
            savings=0.0,
            reason=reason,
        )


def baseline_total(lines: list[CartLine]) -> float:
    return round(sum(line.normal_price * line.quantity for line in lines), 2)


def expand_prices(lines: list[CartLine]) -> list[float]:
    prices: list[float] = []
    for line in lines:
        prices.extend([line.normal_price] * line.quantity)
    return prices


def x_for_y(lines: list[CartLine], *, count: int, bundle_price: float) -> SavingsResult:
    prices = sorted(expand_prices(lines), reverse=True)
    baseline = round(sum(prices), 2)
    bundle_count = len(prices) // count
    remainder = len(prices) % count
    promo = bundle_count * bundle_price
    if remainder:
        promo += sum(sorted(prices[-remainder:]))
    return SavingsResult(baseline, round(promo, 2))


def percentage_off(lines: list[CartLine], *, percentage: float) -> SavingsResult:
    baseline = baseline_total(lines)
    promo = baseline * (1 - percentage / 100)
    return SavingsResult(baseline, round(promo, 2))


def tiered_percentage_off(
    lines: list[CartLine],
    *,
    tiers: dict[int, float],
) -> SavingsResult:
    prices = expand_prices(lines)
    baseline = round(sum(prices), 2)
    quantity = len(prices)
    eligible_counts = [count for count in tiers if quantity >= count]
    if not eligible_counts:
        return SavingsResult(baseline, baseline)
    best_count = max(eligible_counts)
    percentage = tiers[best_count]
    promo = baseline * (1 - percentage / 100)
    return SavingsResult(baseline, round(promo, 2))


def buy_n_pay_m(
    lines: list[CartLine],
    *,
    buy_quantity: int,
    pay_quantity: int,
) -> SavingsResult:
    prices = sorted(expand_prices(lines), reverse=True)
    baseline = round(sum(prices), 2)
    promo = 0.0
    for start in range(0, len(prices), buy_quantity):
        group = prices[start : start + buy_quantity]
        if len(group) < buy_quantity:
            promo += sum(group)
        else:
            promo += sum(group[:pay_quantity])
    return SavingsResult(baseline, round(promo, 2))


def x_plus_y_free_prorated(
    lines: list[CartLine],
    *,
    paid_count: int,
    free_count: int,
) -> SavingsResult:
    baseline = baseline_total(lines)
    bundle_count = paid_count + free_count
    savings = baseline * free_count / bundle_count
    promo = baseline - savings
    return SavingsResult(baseline, round(promo, 2))


def second_half_price(lines: list[CartLine]) -> SavingsResult:
    prices = sorted(expand_prices(lines), reverse=True)
    baseline = round(sum(prices), 2)
    promo = 0.0
    for start in range(0, len(prices), 2):
        pair = prices[start : start + 2]
        if len(pair) == 1:
            promo += pair[0]
        else:
            promo += pair[0] + pair[1] * 0.5
    return SavingsResult(baseline, round(promo, 2))


def weight_discount(
    *,
    grams_used: float,
    normal_price_per_kg: float,
    promo_count: float,
    promo_unit: str,
    promo_price: float,
) -> SavingsResult:
    unit = promo_unit.upper()
    if unit == "GRAM":
        promo_grams = promo_count
    elif unit in {"KG", "KILOGRAM"}:
        promo_grams = promo_count * 1000
    else:
        raise ValueError(f"Unsupported weight promo unit: {promo_unit}")
    baseline = normal_price_per_kg * grams_used / 1000
    promo_units = grams_used / promo_grams
    promo = promo_units * promo_price
    return SavingsResult(round(baseline, 2), round(promo, 2))


def packs_needed(amount_needed: float, amount_per_pack: float) -> int:
    if amount_needed <= 0 or amount_per_pack <= 0:
        raise ValueError("amount_needed and amount_per_pack must be positive")
    return floor((amount_needed + amount_per_pack - 1e-9) / amount_per_pack)


def estimate_product_savings(product: BonusProduct, *, quantity: int = 1) -> DiscountEstimate:
    """Estimate savings for buying whole product packs."""

    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if product.price_before_bonus is None:
        return DiscountEstimate.unsupported(
            discount_code=first_discount_code(product.discount_labels),
            reason="missing_normal_price",
        )
    current_prices = (
        {product.webshop_id: product.current_price} if product.current_price is not None else None
    )
    return estimate_discount_for_lines(
        product.discount_labels,
        [CartLine(product.webshop_id, product.price_before_bonus, quantity)],
        current_unit_prices=current_prices,
    )


def estimate_promotion_savings(
    promotion: BonusPromotion,
    product_quantities: dict[int, int],
    products_by_id: dict[int, BonusProduct],
) -> DiscountEstimate:
    """Estimate savings for one AH promotion across several product IDs."""

    lines = []
    current_unit_prices: dict[int, float | None] = {}
    for product_id, quantity in product_quantities.items():
        if quantity <= 0:
            continue
        product = products_by_id.get(product_id)
        if product is None:
            return DiscountEstimate.unsupported(
                discount_code=first_discount_code(promotion.discount_labels),
                reason=f"unknown_product:{product_id}",
            )
        if product.price_before_bonus is None:
            return DiscountEstimate.unsupported(
                discount_code=first_discount_code(promotion.discount_labels),
                reason=f"missing_normal_price:{product_id}",
            )
        lines.append(CartLine(product_id, product.price_before_bonus, quantity))
        current_unit_prices[product_id] = product.current_price
    return estimate_discount_for_lines(
        promotion.discount_labels,
        lines,
        current_unit_prices=current_unit_prices,
    )


def estimate_discount_for_lines(
    discount_labels: list[DiscountLabel],
    lines: list[CartLine],
    *,
    current_unit_prices: dict[int, float | None] | None = None,
) -> DiscountEstimate:
    if not lines:
        return DiscountEstimate.unsupported(discount_code=None, reason="no_cart_lines")
    baseline = baseline_total(lines)
    if not discount_labels:
        promo_total = total_from_current_prices(lines, current_unit_prices)
        if promo_total is not None:
            return supported_estimate("CURRENT_PRICE", baseline, promo_total)
        return DiscountEstimate.unsupported(
            discount_code=None,
            reason="missing_discount_label",
            baseline_total=baseline,
        )

    code = first_discount_code(discount_labels)
    if code == "DISCOUNT_WEIGHT":
        return current_price_or_unsupported(code, lines, current_unit_prices)
    if code == "DISCOUNT_FIXED_PRICE":
        label = discount_labels[0]
        if label.price is not None:
            return supported_estimate(code, baseline, sum(line.quantity * label.price for line in lines))
        return current_price_or_unsupported(code, lines, current_unit_prices)
    if code in {"DISCOUNT_PERCENTAGE", "DISCOUNT_OP_IS_OP", "DISCOUNT_BUNDLE_BULK"}:
        label = discount_labels[0]
        percentage = label.precise_percentage or label.percentage
        if percentage is not None:
            result = percentage_off(lines, percentage=percentage)
            return supported_estimate(code, result.baseline_total, result.promo_total)
        return current_price_or_unsupported(code, lines, current_unit_prices)
    if code == "DISCOUNT_AMOUNT":
        amount = parse_discount_amount(discount_labels[0].default_description)
        if amount is not None:
            promo_total = sum(max(0.0, line.normal_price - amount) * line.quantity for line in lines)
            return supported_estimate(code, baseline, promo_total)
        return current_price_or_unsupported(code, lines, current_unit_prices)
    if code == "DISCOUNT_X_FOR_Y":
        label = discount_labels[0]
        if label.count and label.price is not None:
            result = x_for_y(lines, count=label.count, bundle_price=label.price)
            return supported_estimate(code, result.baseline_total, result.promo_total)
        return DiscountEstimate.unsupported(
            discount_code=code,
            reason="missing_x_for_y_fields",
            baseline_total=baseline,
        )
    if code == "DISCOUNT_X_PLUS_Y_FREE":
        label = discount_labels[0]
        if label.count and label.free_count:
            result = x_plus_y_free_prorated(
                lines,
                paid_count=label.count,
                free_count=label.free_count,
            )
            return supported_estimate(
                code,
                result.baseline_total,
                result.promo_total,
                notes=(x_plus_y_activation_note(label.count, label.free_count),),
            )
        return DiscountEstimate.unsupported(
            discount_code=code,
            reason="missing_x_plus_y_fields",
            baseline_total=baseline,
        )
    if code == "DISCOUNT_ONE_HALF_PRICE":
        result = second_half_price(lines)
        return supported_estimate(code, result.baseline_total, result.promo_total)
    if code == "DISCOUNT_TIERED_PERCENT":
        tiers = {
            label.count: label.precise_percentage or label.percentage
            for label in discount_labels
            if label.count and (label.precise_percentage is not None or label.percentage is not None)
        }
        if tiers:
            result = tiered_percentage_off(lines, tiers=tiers)
            return supported_estimate(code, result.baseline_total, result.promo_total)
        return DiscountEstimate.unsupported(
            discount_code=code,
            reason="missing_tier_fields",
            baseline_total=baseline,
        )
    if code == "DISCOUNT_BONUS":
        return current_price_or_unsupported(code, lines, current_unit_prices)
    return DiscountEstimate.unsupported(
        discount_code=code,
        reason="unsupported_discount_code",
        baseline_total=baseline,
    )


def total_from_current_prices(
    lines: list[CartLine],
    current_unit_prices: dict[int, float | None] | None,
) -> float | None:
    if not current_unit_prices:
        return None
    promo_total = 0.0
    for line in lines:
        current_price = current_unit_prices.get(line.product_id)
        if current_price is None:
            return None
        promo_total += current_price * line.quantity
    return round(promo_total, 2)


def current_price_or_unsupported(
    code: str | None,
    lines: list[CartLine],
    current_unit_prices: dict[int, float | None] | None,
) -> DiscountEstimate:
    baseline = baseline_total(lines)
    promo_total = total_from_current_prices(lines, current_unit_prices)
    if promo_total is None:
        return DiscountEstimate.unsupported(
            discount_code=code,
            reason="missing_current_price",
            baseline_total=baseline,
        )
    return supported_estimate(code, baseline, promo_total)


def supported_estimate(
    code: str | None,
    baseline: float,
    promo_total: float,
    *,
    notes: tuple[str, ...] = (),
) -> DiscountEstimate:
    baseline = round(baseline, 2)
    promo_total = round(promo_total, 2)
    return DiscountEstimate(
        supported=True,
        discount_code=code,
        baseline_total=baseline,
        promo_total=promo_total,
        savings=round(baseline - promo_total, 2),
        notes=notes,
    )


def first_discount_code(discount_labels: list[DiscountLabel]) -> str | None:
    return discount_labels[0].code if discount_labels else None


def parse_discount_amount(description: str | None) -> float | None:
    if not description:
        return None
    match = re.search(r"(\d+(?:[,.]\d+)?)", description)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def x_plus_y_activation_note(paid_count: int, free_count: int) -> str:
    minimum_quantity = paid_count + free_count
    return (
        f"{paid_count}+{free_count} gratis is prorated in the recipe savings; "
        f"buy at least {minimum_quantity} qualifying products to activate this bonus."
    )
