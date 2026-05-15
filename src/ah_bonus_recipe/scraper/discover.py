from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ah_bonus_recipe.ah_client import AHClient
from ah_bonus_recipe.config import AH_WEB_BONUS_URL, BROWSER_USER_AGENT, DISCOVERY_DIR


KEYWORD_PATTERN = re.compile(
    r".{0,140}(apolloConfig|bonusCategories|bonusPromotions|productCard|"
    r"tradeItem|graphql|x-client-name|mobile-services).{0,220}",
    flags=re.IGNORECASE,
)


def run_discovery(
    output_dir: Path = DISCOVERY_DIR,
    *,
    sample_category: str | None = None,
    max_chunks: int | None = None,
) -> dict[str, Any]:
    """Capture useful AH web/API artifacts for scraper development."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / timestamp
    web_dir = run_dir / "web"
    chunk_dir = web_dir / "chunks"
    api_dir = run_dir / "api"
    web_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    api_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "run_dir": str(run_dir),
        "captured_at": timestamp,
        "web": {},
        "api": {},
    }

    html = fetch_web_bonus_page()
    html_path = web_dir / "bonus_page.html"
    html_path.write_text(html, encoding="utf-8")
    chunk_urls = extract_chunk_urls(html)
    if max_chunks is not None:
        chunk_urls = chunk_urls[:max_chunks]
    summary["web"]["chunk_count"] = len(chunk_urls)
    summary["web"]["apollo_config_snippet"] = snippet_around(html, "apolloConfig")

    keyword_hits = []
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for url in chunk_urls:
            text = client.get(url).text
            path = chunk_dir / safe_filename(url)
            path.write_text(text, encoding="utf-8")
            for match in KEYWORD_PATTERN.finditer(text):
                keyword_hits.append({"file": path.name, "snippet": compact(match.group(0))})

    summary["web"]["keyword_hits"] = keyword_hits[:40]
    (web_dir / "keyword_hits.json").write_text(
        json.dumps(summary["web"]["keyword_hits"], indent=2), encoding="utf-8"
    )

    with AHClient() as ah:
        token_payload = ah.get_anonymous_token()
        summary["api"]["anonymous_token"] = {
            "expires_in": token_payload.get("expires_in"),
            "access_token_saved": False,
        }

        metadata = ah.get_bonus_metadata()
        write_json(api_dir / "bonus_metadata.json", metadata)
        periods = metadata.get("periods", [])
        if not periods:
            raise RuntimeError("AH bonus metadata response did not include any periods")

        current_period = periods[0]
        period_start = current_period["bonusStartDate"]
        period_end = current_period["bonusEndDate"]
        summary["api"]["current_period"] = {
            "start": period_start,
            "end": period_end,
            "next_period_visible_from": current_period.get("nextPeriodVisibleFrom"),
        }
        if len(periods) > 1:
            summary["api"]["next_period"] = {
                "start": periods[1].get("bonusStartDate"),
                "end": periods[1].get("bonusEndDate"),
            }

        category_items = current_period_category_items(current_period)
        summary["api"]["category_count"] = len(category_items)
        chosen_item = choose_category(category_items, sample_category)
        if not chosen_item:
            raise RuntimeError("No NATIONAL category URL found in AH bonus metadata")

        section = ah.get_bonus_section_from_metadata_url(chosen_item["url"])
        section_path = api_dir / f"bonus_section_{safe_slug(chosen_item['description'])}.json"
        write_json(section_path, section)

        items = section.get("bonusGroupOrProducts", [])
        groups = [item["bonusGroup"] for item in items if item.get("bonusGroup")]
        products = [item["product"] for item in items if item.get("product")]
        summary["api"]["sample_section"] = {
            "category": chosen_item["description"],
            "path": str(section_path),
            "item_count": len(items),
            "direct_product_count": len(products),
            "group_count": len(groups),
        }

        group_with_empty_products = next((g for g in groups if not g.get("products")), None)
        if group_with_empty_products:
            group_id = str(group_with_empty_products["id"])
            group_payload = ah.get_bonus_group_products(
                group_id,
                period_start=period_start,
                period_end=period_end,
            )
            group_path = api_dir / f"bonus_group_{group_id}.json"
            write_json(group_path, group_payload)
            group_products = (
                group_payload.get("data", {})
                .get("bonusPromotions", [{}])[0]
                .get("products", [])
            )
            summary["api"]["sample_group"] = {
                "id": group_id,
                "title": group_with_empty_products.get("segmentDescription"),
                "path": str(group_path),
                "product_count": len(group_products),
            }
            if group_products:
                products.insert(0, {"webshopId": group_products[0]["id"]})

        if products:
            product_id = int(products[0]["webshopId"])
            detail = ah.get_product_detail(product_id)
            detail_path = api_dir / f"product_{product_id}_detail.json"
            write_json(detail_path, detail)
            trade_item = detail.get("tradeItem", {})
            summary["api"]["sample_product_detail"] = {
                "webshop_id": product_id,
                "path": str(detail_path),
                "has_product_card": "productCard" in detail,
                "has_trade_item": "tradeItem" in detail,
                "has_ingredients": bool(trade_item.get("foodAndBeverageIngredientStatement")),
                "has_allergens": bool(trade_item.get("allergenInformation")),
                "has_nutrition": bool(trade_item.get("nutritionalInformation")),
            }

    write_json(run_dir / "summary.json", summary)
    (run_dir / "report.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def fetch_web_bonus_page() -> str:
    headers = {
        "user-agent": BROWSER_USER_AGENT,
        "accept-language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = httpx.get(AH_WEB_BONUS_URL, headers=headers, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return response.text


def extract_chunk_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = set()
    for tag in soup.find_all("script"):
        src = tag.get("src")
        if src and "/_next/static/chunks/" in src and src.endswith(".js"):
            urls.add(urljoin(AH_WEB_BONUS_URL, src))
    return sorted(urls)


def current_period_category_items(period: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for tab in period.get("tabs", []):
        if tab.get("description") != "Alle Bonus":
            continue
        for item in tab.get("urlMetadataList", []):
            if item.get("bonusType") == "NATIONAL" and item.get("url"):
                items.append(item)
    return items


def choose_category(
    category_items: list[dict[str, Any]],
    sample_category: str | None,
) -> dict[str, Any] | None:
    if not category_items:
        return None
    if sample_category:
        lowered = sample_category.lower()
        for item in category_items:
            if lowered in item.get("description", "").lower():
                return item
    for item in category_items:
        if item.get("description") == "Groente, aardappelen":
            return item
    return category_items[0]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def snippet_around(text: str, needle: str, radius: int = 500) -> str | None:
    index = text.find(needle)
    if index < 0:
        return None
    start = max(index - radius, 0)
    end = min(index + len(needle) + radius, len(text))
    return compact(text[start:end])


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def safe_filename(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", url.split("/")[-1])[:180]


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"


def render_report(summary: dict[str, Any]) -> str:
    api = summary["api"]
    web = summary["web"]
    lines = [
        "# AH Bonus Discovery",
        "",
        f"Captured at: `{summary['captured_at']}`",
        f"Run directory: `{summary['run_dir']}`",
        "",
        "## Web App Clues",
        "",
        f"- Downloaded Next.js chunk count: {web.get('chunk_count')}",
        "- The AH Bonus page is an Apollo/GraphQL app.",
        "- The server-rendered page includes `apolloConfig` with client headers.",
        "",
        "## Mobile API Clues",
        "",
        "- Anonymous token endpoint works: `POST /mobile-auth/v1/auth/token/anonymous`.",
        "- Required headers include `x-client-name`, `x-client-version`, and `x-application: AHWEBSHOP`.",
        "- Weekly metadata endpoint works: `GET /mobile-services/bonuspage/v3/metadata`.",
        "- Category section endpoint comes from metadata URLs under `/mobile-services/bonuspage/v2/section`.",
        "- Group cards with empty `products` can be expanded through `POST /graphql` and `bonusPromotions`.",
        "- Product details work through `GET /mobile-services/product/detail/v4/fir/{webshop_id}`.",
        "",
        "## Current Sample",
        "",
        f"- Current period: {api.get('current_period', {}).get('start')} to "
        f"{api.get('current_period', {}).get('end')}",
        f"- Next period: {api.get('next_period', {}).get('start')} to "
        f"{api.get('next_period', {}).get('end')}",
        f"- National category count: {api.get('category_count')}",
    ]
    if sample := api.get("sample_section"):
        lines.extend(
            [
                f"- Sample category: {sample.get('category')}",
                f"- Section groups: {sample.get('group_count')}",
                f"- Section direct products: {sample.get('direct_product_count')}",
            ]
        )
    if group := api.get("sample_group"):
        lines.append(f"- Expanded sample group `{group.get('id')}` with {group.get('product_count')} products")
    if product := api.get("sample_product_detail"):
        lines.extend(
            [
                f"- Product detail sample: `{product.get('webshop_id')}`",
                f"- Has ingredients: {product.get('has_ingredients')}",
                f"- Has allergens: {product.get('has_allergens')}",
                f"- Has nutrition: {product.get('has_nutrition')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Next Implementation Step",
            "",
            "Normalize raw metadata, sections, expanded groups, and product details into "
            "`BonusWeekDataset`, then add persistence to SQLite or Parquet.",
            "",
        ]
    )
    return "\n".join(lines)
