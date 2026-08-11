from __future__ import annotations

import os

import pytest

from sreality_tracker.scraper.client import ListingKind, SrealityClient


@pytest.mark.live
def test_live_search_pages_for_both_categories() -> None:
    if os.getenv("SREALITY_RUN_LIVE_TESTS") != "1":
        pytest.skip("Set SREALITY_RUN_LIVE_TESTS=1 to enable the polite live check")

    with SrealityClient(min_delay_seconds=0.75, max_attempts=2) as client:
        chata_html = client.fetch_search_page(ListingKind.CHATA)
        chalupa_html = client.fetch_search_page(ListingKind.CHALUPA)

    assert "__NEXT_DATA__" in chata_html
    assert "__NEXT_DATA__" in chalupa_html
