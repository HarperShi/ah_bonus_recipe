from datetime import date, datetime, timezone

from ah_bonus_recipe.models import BonusProduct, BonusWeekDataset
from ah_bonus_recipe.web.api import dataset_status


def test_dataset_status_summarizes_week_and_candidates() -> None:
    dataset = BonusWeekDataset(
        week_start=date(2026, 5, 11),
        week_end=date(2026, 5, 17),
        scraped_at=datetime.now(timezone.utc),
        source_url="https://www.ah.nl/bonus",
        products=[
            BonusProduct(
                webshop_id=1,
                title="AH Pasta",
                category="Pasta, rijst, wereldkeuken",
                ingredients="durum wheat",
            )
        ],
        promotions=[],
    )

    status = dataset_status(dataset)

    assert status.dataset_exists is True
    assert status.week_start == "2026-05-11"
    assert status.week_end == "2026-05-17"
    assert status.product_count == 1
    assert status.candidate_product_count == 1
