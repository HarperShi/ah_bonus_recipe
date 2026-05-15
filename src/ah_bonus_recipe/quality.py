from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ah_bonus_recipe.config import PROCESSED_DATA_DIR
from ah_bonus_recipe.models import BonusProduct, BonusWeekDataset
from ah_bonus_recipe.pricing import estimate_product_savings


DEFAULT_DATASET_PATH = PROCESSED_DATA_DIR / "latest_bonus_week.json"
DEFAULT_REPORT_PATH = PROCESSED_DATA_DIR / "latest_quality_report.json"


def generate_quality_report(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_path: Path = DEFAULT_REPORT_PATH,
    max_issue_products: int | None = None,
) -> dict[str, Any]:
    dataset = BonusWeekDataset.model_validate_json(dataset_path.read_text(encoding="utf-8"))
    report = build_quality_report(
        dataset,
        dataset_path=dataset_path,
        max_issue_products=max_issue_products,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def build_quality_report(
    dataset: BonusWeekDataset,
    *,
    dataset_path: Path | None = None,
    max_issue_products: int | None = None,
) -> dict[str, Any]:
    products = dataset.products
    promotions = dataset.promotions
    product_discount_codes = Counter(
        label.code for product in products for label in product.discount_labels
    )
    promotion_discount_codes = Counter(
        label.code for promotion in promotions for label in promotion.discount_labels
    )

    issue_rows = []
    issue_counts: Counter[str] = Counter()
    discount_support = Counter()
    unsupported_reasons: Counter[str] = Counter()
    savings_examples = []

    for product in products:
        issues = product_issue_codes(product)
        issue_counts.update(issues)
        if issues and (max_issue_products is None or len(issue_rows) < max_issue_products):
            issue_rows.append(
                {
                    "webshop_id": product.webshop_id,
                    "title": product.title,
                    "issues": issues,
                }
            )

        estimate = estimate_product_savings(product, quantity=1)
        if estimate.supported:
            discount_support["supported"] += 1
            if estimate.savings > 0 and len(savings_examples) < 25:
                savings_examples.append(
                    {
                        "webshop_id": product.webshop_id,
                        "title": product.title,
                        **asdict(estimate),
                    }
                )
        else:
            discount_support["unsupported"] += 1
            unsupported_reasons[estimate.reason or "unknown"] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "week_start": dataset.week_start.isoformat(),
        "week_end": dataset.week_end.isoformat(),
        "product_count": len(products),
        "promotion_count": len(promotions),
        "field_coverage": field_coverage(products),
        "issue_counts": dict(sorted(issue_counts.items())),
        "products_with_issues_count": sum(1 for product in products if product_issue_codes(product)),
        "products_with_issues": issue_rows,
        "discount_label_codes": dict(product_discount_codes.most_common()),
        "promotion_discount_label_codes": dict(promotion_discount_codes.most_common()),
        "discount_support": dict(discount_support),
        "unsupported_discount_reasons": dict(unsupported_reasons.most_common()),
        "sample_savings_for_one_pack": savings_examples,
    }


def field_coverage(products: list[BonusProduct]) -> dict[str, Any]:
    fields = {
        "price_before_bonus": lambda product: product.price_before_bonus is not None,
        "current_price": lambda product: product.current_price is not None,
        "sales_unit_size": lambda product: bool(product.sales_unit_size),
        "ingredients": lambda product: bool(product.ingredients),
        "allergens": lambda product: bool(product.allergens),
        "nutrition": lambda product: bool(product.nutrition),
        "description": lambda product: bool(product.description),
        "images": lambda product: bool(product.images),
        "discount_labels": lambda product: bool(product.discount_labels),
    }
    coverage = {}
    total = len(products)
    for name, predicate in fields.items():
        present = sum(1 for product in products if predicate(product))
        coverage[name] = {
            "present": present,
            "missing": total - present,
            "present_ratio": round(present / total, 4) if total else 0,
        }
    return coverage


def product_issue_codes(product: BonusProduct) -> list[str]:
    issues = []
    if product.price_before_bonus is None:
        issues.append("missing_price_before_bonus")
    if not product.sales_unit_size:
        issues.append("missing_sales_unit_size")
    if not product.ingredients:
        issues.append("missing_ingredients")
    if not product.allergens:
        issues.append("missing_allergens")
    if not product.nutrition:
        issues.append("missing_nutrition")
    if not product.discount_labels:
        issues.append("missing_discount_labels")
    estimate = estimate_product_savings(product, quantity=1)
    if not estimate.supported:
        issues.append(f"discount_unestimated:{estimate.reason}")
    return issues
