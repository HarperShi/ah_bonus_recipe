from __future__ import annotations

from dataclasses import dataclass
from math import floor


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
