from ah_bonus_recipe.scraper.weekly import (
    extract_group_products,
    extract_product_id,
    normalize_promotion,
    selected_metadata_items,
)


def test_selected_metadata_items_filters_and_deduplicates_urls() -> None:
    period = {
        "tabs": [
            {
                "description": "Alle Bonus",
                "urlMetadataList": [
                    {"url": "bonuspage/v2/section?a=1", "bonusType": "NATIONAL"},
                    {"url": "bonuspage/v2/section?a=1", "bonusType": "NATIONAL"},
                    {"url": "bonuspage/v2/section?a=2", "bonusType": "ETOS"},
                    {"url": "bonuspage/v2/section?a=3", "bonusType": "AHONLINE"},
                ],
            },
            {
                "description": "Uitgelicht",
                "urlMetadataList": [{"url": "bonuspage/v2/section?a=4", "bonusType": "NATIONAL"}],
            },
        ]
    }

    items = selected_metadata_items(period, ("NATIONAL", "AHONLINE"))

    assert [item["url"] for item in items] == [
        "bonuspage/v2/section?a=1",
        "bonuspage/v2/section?a=3",
    ]


def test_extract_group_products_flattens_graphql_promotions() -> None:
    payload = {
        "data": {
            "bonusPromotions": [
                {"products": [{"id": 1}, {"id": 2}]},
                {"products": [{"id": 3}]},
            ]
        }
    }

    assert extract_group_products(payload) == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_extract_product_id_accepts_known_shapes() -> None:
    assert extract_product_id({"webshopId": "123"}) == 123
    assert extract_product_id({"id": 456}) == 456
    assert extract_product_id({"productId": "789"}) == 789
    assert extract_product_id({}) is None


def test_normalize_promotion_from_bonus_group() -> None:
    promotion = normalize_promotion(
        {
            "id": "784569",
            "segmentDescription": "Alle AH Kleinverpakkingen groentegemak",
            "category": "Groente, aardappelen",
            "promotionType": "NATIONAL",
            "bonusStartDate": "2026-05-11",
            "bonusEndDate": "2026-05-17",
            "discountDescription": "2 VOOR 2.49",
            "discountLabels": [{"code": "DISCOUNT_X_FOR_Y", "count": 2, "price": 2.49}],
        },
        [395948, 230848],
    )

    assert promotion.id == "784569"
    assert promotion.title == "Alle AH Kleinverpakkingen groentegemak"
    assert promotion.product_ids == [395948, 230848]
    assert promotion.discount_labels[0].code == "DISCOUNT_X_FOR_Y"
