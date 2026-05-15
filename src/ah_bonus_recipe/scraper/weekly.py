from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from ah_bonus_recipe.ah_client import AHClient
from ah_bonus_recipe.config import AH_WEB_BONUS_URL, PROCESSED_DATA_DIR, RAW_DATA_DIR
from ah_bonus_recipe.models import BonusPromotion, BonusWeekDataset, DiscountLabel
from ah_bonus_recipe.scraper.discover import safe_slug
from ah_bonus_recipe.scraper.normalize import normalize_product_detail


DEFAULT_PROMOTION_TYPES = ("NATIONAL", "AHONLINE")


def scrape_bonus_week(
    *,
    raw_output_dir: Path = RAW_DATA_DIR,
    processed_output_dir: Path = PROCESSED_DATA_DIR,
    period: str = "current",
    promotion_types: tuple[str, ...] = DEFAULT_PROMOTION_TYPES,
    include_store_only: bool = False,
    filter_unavailable_group_products: bool = False,
    max_products: int | None = None,
    request_delay_seconds: float = 0.05,
) -> dict[str, Any]:
    """Scrape a complete AH Bonus period into raw and normalized datasets."""

    scraped_at = datetime.now(timezone.utc)
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    processed_output_dir.mkdir(parents=True, exist_ok=True)

    with AHClient() as ah:
        metadata = ah.get_bonus_metadata()
        period_payload = select_period(metadata, period)
        week_start = date.fromisoformat(period_payload["bonusStartDate"])
        week_end = date.fromisoformat(period_payload["bonusEndDate"])

        week_dir = raw_output_dir / f"{week_start}_to_{week_end}"
        sections_dir = week_dir / "sections"
        groups_dir = week_dir / "groups"
        products_dir = week_dir / "products"
        for path in (sections_dir, groups_dir, products_dir):
            path.mkdir(parents=True, exist_ok=True)

        write_json(week_dir / "metadata.json", metadata)
        metadata_items = selected_metadata_items(period_payload, promotion_types)

        raw_promotions: dict[str, dict[str, Any]] = {}
        promotion_product_ids: dict[str, set[int]] = defaultdict(set)
        product_ids: set[int] = set()
        failed_sections: list[dict[str, Any]] = []
        failed_groups: list[dict[str, Any]] = []
        failed_products: list[dict[str, Any]] = []

        for item in metadata_items:
            section_key = section_filename(item)
            try:
                section = ah.get_bonus_section_from_metadata_url(item["url"])
            except httpx.HTTPError as exc:
                failed_sections.append({"url": item.get("url"), "error": repr(exc)})
                continue
            write_json(sections_dir / f"{section_key}.json", section)

            for entry in section.get("bonusGroupOrProducts", []):
                if group := entry.get("bonusGroup"):
                    if group.get("storeOnlyPromotion") and not include_store_only:
                        continue
                    group_id = str(group["id"])
                    raw_promotions[group_id] = group
                    embedded_products = group.get("products") or []
                    if embedded_products:
                        for product in embedded_products:
                            product_id = extract_product_id(product)
                            if product_id is not None:
                                product_ids.add(product_id)
                                promotion_product_ids[group_id].add(product_id)
                        continue
                    try:
                        group_payload = ah.get_bonus_group_products(
                            group_id,
                            period_start=str(week_start),
                            period_end=str(week_end),
                            filter_unavailable_products=filter_unavailable_group_products,
                        )
                    except (httpx.HTTPError, RuntimeError) as exc:
                        failed_groups.append({"id": group_id, "title": group.get("segmentDescription"), "error": repr(exc)})
                        continue
                    write_json(groups_dir / f"{group_id}.json", group_payload)
                    expanded_products = extract_group_products(group_payload)
                    for product in expanded_products:
                        product_id = extract_product_id(product)
                        if product_id is not None:
                            product_ids.add(product_id)
                            promotion_product_ids[group_id].add(product_id)

                if product := entry.get("product"):
                    product_id = extract_product_id(product)
                    if product_id is None:
                        continue
                    product_ids.add(product_id)
                    promotion_id = str(product.get("bonusSegmentId") or product.get("segmentId") or product_id)
                    raw_promotions.setdefault(promotion_id, product)
                    promotion_product_ids[promotion_id].add(product_id)

        discovered_product_id_count = len(product_ids)
        sorted_product_ids = sorted(product_ids)
        if max_products is not None:
            sorted_product_ids = sorted_product_ids[:max_products]

        normalized_products = []
        for index, product_id in enumerate(sorted_product_ids, start=1):
            try:
                detail = ah.get_product_detail(product_id)
            except httpx.HTTPError as exc:
                failed_products.append({"webshop_id": product_id, "error": repr(exc)})
                continue
            write_json(products_dir / f"{product_id}.json", detail)
            normalized_products.append(normalize_product_detail(detail))
            if request_delay_seconds and index < len(sorted_product_ids):
                time.sleep(request_delay_seconds)

    normalized_product_ids = {product.webshop_id for product in normalized_products}
    promotions = [
        normalize_promotion(raw, sorted(product_ids_for_promotion & normalized_product_ids))
        for promotion_id, raw in sorted(raw_promotions.items())
        if (product_ids_for_promotion := promotion_product_ids.get(promotion_id, set())) & normalized_product_ids
    ]
    dataset = BonusWeekDataset(
        week_start=week_start,
        week_end=week_end,
        scraped_at=scraped_at,
        source_url=AH_WEB_BONUS_URL,
        promotions=promotions,
        products=sorted(normalized_products, key=lambda product: product.webshop_id),
    )

    dataset_payload = dataset_payload_without_raw(dataset)
    products_payload = [product_payload_without_raw(product) for product in dataset.products]
    processed_week_path = processed_output_dir / f"bonus_week_{week_start}_to_{week_end}.json"
    latest_week_path = processed_output_dir / "latest_bonus_week.json"
    latest_products_path = processed_output_dir / "latest_products.json"
    write_json(processed_week_path, dataset_payload)
    write_json(latest_week_path, dataset_payload)
    write_json(latest_products_path, products_payload)

    summary = {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "scraped_at": scraped_at.isoformat(),
        "promotion_types": list(promotion_types),
        "raw_dir": str(week_dir),
        "processed_week_path": str(processed_week_path),
        "latest_week_path": str(latest_week_path),
        "latest_products_path": str(latest_products_path),
        "metadata_section_count": len(metadata_items),
        "discovered_product_id_count": discovered_product_id_count,
        "requested_product_detail_count": len(sorted_product_ids),
        "promotion_count": len(promotions),
        "product_count": len(dataset.products),
        "failed_sections": failed_sections,
        "failed_groups": failed_groups,
        "failed_products": failed_products,
        "truncated_by_max_products": max_products is not None,
    }
    write_json(week_dir / "summary.json", summary)
    return summary


def select_period(metadata: dict[str, Any], period: str) -> dict[str, Any]:
    periods = metadata.get("periods", [])
    if not periods:
        raise RuntimeError("AH bonus metadata response did not include any periods")
    if period == "current":
        return periods[0]
    if period == "next":
        if len(periods) < 2:
            raise RuntimeError("AH bonus metadata response did not include a next period")
        return periods[1]
    for item in periods:
        if item.get("bonusStartDate") == period:
            return item
    raise ValueError(f"Unknown period {period!r}; use 'current', 'next', or a bonusStartDate")


def selected_metadata_items(
    period_payload: dict[str, Any],
    promotion_types: tuple[str, ...],
) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    selected: list[dict[str, Any]] = []
    allowed_types = {promotion_type.upper() for promotion_type in promotion_types}
    for tab in period_payload.get("tabs", []):
        if tab.get("description") != "Alle Bonus":
            continue
        for item in tab.get("urlMetadataList", []):
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            bonus_type = str(item.get("bonusType", "")).upper()
            if allowed_types and bonus_type not in allowed_types:
                continue
            seen_urls.add(url)
            selected.append(item)
    return selected


def extract_group_products(group_payload: dict[str, Any]) -> list[dict[str, Any]]:
    promotions = group_payload.get("data", {}).get("bonusPromotions", [])
    products: list[dict[str, Any]] = []
    for promotion in promotions:
        products.extend(promotion.get("products") or [])
    return products


def extract_product_id(product: dict[str, Any]) -> int | None:
    product_id = product.get("webshopId") or product.get("id") or product.get("productId")
    if product_id is None:
        return None
    return int(product_id)


def normalize_promotion(raw: dict[str, Any], product_ids: list[int]) -> BonusPromotion:
    promotion_id = str(raw.get("id") or raw.get("bonusSegmentId") or raw.get("segmentId") or raw.get("webshopId"))
    title = (
        raw.get("segmentDescription")
        or raw.get("bonusSegmentDescription")
        or raw.get("title")
        or f"Promotion {promotion_id}"
    )
    return BonusPromotion(
        id=promotion_id,
        title=title,
        category=raw.get("category") or raw.get("mainCategory"),
        promotion_type=raw.get("promotionType"),
        bonus_start_date=raw.get("bonusStartDate"),
        bonus_end_date=raw.get("bonusEndDate"),
        discount_description=raw.get("discountDescription") or raw.get("bonusMechanism"),
        discount_labels=[DiscountLabel.model_validate(item) for item in raw.get("discountLabels", [])],
        product_ids=product_ids,
        raw=raw,
    )


def dataset_payload_without_raw(dataset: BonusWeekDataset) -> dict[str, Any]:
    return dataset.model_dump(
        mode="json",
        exclude={
            "promotions": {"__all__": {"raw"}},
            "products": {"__all__": {"raw"}},
        },
    )


def product_payload_without_raw(product: Any) -> dict[str, Any]:
    return product.model_dump(mode="json", exclude={"raw"})


def section_filename(item: dict[str, Any]) -> str:
    bonus_type = safe_slug(str(item.get("bonusType") or "bonus"))
    description = safe_slug(str(item.get("description") or "section"))
    return f"{bonus_type}_{description}"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
