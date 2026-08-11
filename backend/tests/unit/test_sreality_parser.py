from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from sreality_tracker.domain.listings import ListingKind
from sreality_tracker.scraper.parser import (
    ParseError,
    parse_detail_data,
    parse_detail_fixture,
    parse_search_fixture,
    parse_search_html,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "sreality"


def load_fixture(name: str) -> dict[str, Any]:
    value = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize(
    ("filename", "kind", "total"),
    [
        ("search_chata.json", ListingKind.CHATA, 2409),
        ("search_chalupa.json", ListingKind.CHALUPA, 1174),
    ],
)
def test_search_fixtures_parse_both_categories(
    filename: str, kind: ListingKind, total: int
) -> None:
    fixture = load_fixture(filename)

    page = parse_search_fixture(fixture, kind)

    assert page.kind is kind
    assert page.page == 1
    assert page.limit == 22
    assert page.total == total
    assert len(page.listings) == 2
    assert all(listing.kind is kind for listing in page.listings)
    assert all(listing.sreality_id > 0 for listing in page.listings)
    assert page.listings[0].name == fixture["data"]["results"][0]["name"]
    assert (
        page.listings[0].images[0].source_url == fixture["data"]["results"][0]["images"][0]["url"]
    )


@pytest.mark.parametrize(
    ("filename", "kind"),
    [
        ("detail_chata.json", ListingKind.CHATA),
        ("detail_chalupa.json", ListingKind.CHALUPA),
    ],
)
def test_detail_fixtures_preserve_text_params_and_image_metadata(
    filename: str, kind: ListingKind
) -> None:
    fixture = load_fixture(filename)
    source = fixture["data"]

    detail = parse_detail_fixture(
        fixture,
        sreality_id=987654,
        source_url="https://www.sreality.cz/detail/example",
    )

    assert detail.kind is kind
    assert detail.sreality_id == 987654
    assert detail.name == source["name"]
    assert detail.description == source["description"]
    assert detail.price_note == source["params"]["priceNote"]
    assert detail.params == source["params"]
    assert detail.raw == source
    assert len(detail.images) == len(source["images"])
    assert detail.images[0].source_id == str(source["images"][0]["id"])
    assert detail.images[0].source_url == source["images"][0]["url"]
    assert detail.images[0].alt == source["images"][0]["alt"]
    assert detail.images[0].width == source["images"][0]["width"]
    assert detail.images[0].height == source["images"][0]["height"]


def test_missing_optional_fixture_maps_to_none_and_empty_images() -> None:
    fixture = load_fixture("detail_missing_optional.json")

    detail = parse_detail_fixture(
        fixture,
        sreality_id=123,
        source_url="https://www.sreality.cz/detail/missing",
    )

    assert detail.images == ()
    assert detail.building_area_m2 is None
    assert detail.floor_area_m2 is None
    assert detail.garden_area_m2 is None
    assert detail.locality.latitude == fixture["data"]["locality"]["latitude"]
    assert detail.locality.longitude == fixture["data"]["locality"]["longitude"]


def test_zero_price_is_preserved_but_excluded_from_analytics() -> None:
    fixture = load_fixture("detail_chata.json")
    data = deepcopy(fixture["data"])
    data["priceCzk"] = 0
    data["priceCzkPerSqM"] = 0

    detail = parse_detail_data(
        data,
        sreality_id=123,
        source_url="https://www.sreality.cz/detail/zero",
        expected_kind=ListingKind.CHATA,
    )

    assert detail.price.source_price_czk == 0
    assert detail.price.price_czk is None
    assert detail.price.price_on_request is True
    assert detail.price.derived_price_per_sqm_czk is None


def test_unknown_fields_are_preserved_without_affecting_typed_fields() -> None:
    fixture = load_fixture("detail_chata.json")
    data = deepcopy(fixture["data"])
    data["futureTopLevelField"] = {"nested": "preserved"}
    data["params"]["futureParam"] = [1, 2, 3]

    detail = parse_detail_data(
        data,
        sreality_id=123,
        source_url="https://www.sreality.cz/detail/future",
        expected_kind=ListingKind.CHATA,
    )

    assert detail.raw["futureTopLevelField"] == {"nested": "preserved"}
    assert detail.params["futureParam"] == [1, 2, 3]
    assert detail.kind is ListingKind.CHATA


def test_search_html_extracts_estates_query() -> None:
    fixture = load_fixture("search_chata.json")
    next_data = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": ["estatesSearch", fixture["query_params"]],
                            "state": {"data": fixture["data"]},
                        }
                    ]
                }
            }
        }
    }
    html = (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(next_data)
        + "</script></html>"
    )

    page = parse_search_html(html, ListingKind.CHATA)

    assert page.total == 2409
    assert len(page.listings) == 2


def test_required_category_mismatch_fails_clearly() -> None:
    fixture = load_fixture("detail_chata.json")

    with pytest.raises(ParseError, match="does not match"):
        parse_detail_data(
            fixture["data"],
            sreality_id=123,
            source_url="https://www.sreality.cz/detail/wrong",
            expected_kind=ListingKind.CHALUPA,
        )
