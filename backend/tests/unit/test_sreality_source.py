from __future__ import annotations

import json
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import Mock

from sreality_tracker.domain.listings import ListingKind
from sreality_tracker.scraper.client import ResponseValidationError
from sreality_tracker.scraper.parser import extract_detail_paths_html
from sreality_tracker.scraper.source import SrealityListingSource

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "sreality"


def load_fixture(filename: str) -> dict[str, Any]:
    value = json.loads((FIXTURE_ROOT / filename).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def next_data_html(
    fixture: dict[str, Any], *, page: int | None = None, links: Sequence[tuple[int, str]] = ()
) -> str:
    query_params = deepcopy(fixture.get("query_params", {}))
    if page is not None:
        query_params["page"] = page
    payload = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": [fixture["query_name"], query_params],
                            "state": {"data": fixture["data"]},
                        }
                    ]
                }
            }
        }
    }
    anchors = "".join(f'<a href="{path}?foo=bar">{listing_id}</a>' for listing_id, path in links)
    return f'{anchors}<script id="__NEXT_DATA__">{json.dumps(payload)}</script>'


class FakeClient:
    def __init__(
        self,
        search_pages: dict[int, str],
        detail_html: str,
        *,
        detail_error: Exception | None = None,
    ) -> None:
        self.search_pages = search_pages
        self.detail_html = detail_html
        self.detail_error = detail_error
        self.search_calls: list[tuple[ListingKind, int]] = []
        self.detail_calls: list[str] = []

    def fetch_search_page(self, kind: ListingKind, page: int = 1) -> str:
        self.search_calls.append((kind, page))
        return self.search_pages[page]

    def fetch_detail_page(self, detail_path: str) -> str:
        self.detail_calls.append(detail_path)
        if self.detail_error is not None:
            raise self.detail_error
        return self.detail_html


def test_detail_paths_are_canonical_and_keyed_by_external_id() -> None:
    html = (
        '<a href="/detail/prodej/dum/chata/example/123?tracking=1">one</a>'
        '<a href="https://www.sreality.cz/detail/prodej/dum/chata/other/456/">two</a>'
        '<a href="/hledani/prodej/domy/chaty">ignore</a>'
    )

    assert extract_detail_paths_html(html) == {
        123: "/detail/prodej/dum/chata/example/123",
        456: "/detail/prodej/dum/chata/other/456",
    }


def test_source_traverses_pages_deduplicates_and_fetches_matching_details() -> None:
    search_fixture = load_fixture("search_chata.json")
    first_data = deepcopy(search_fixture["data"])
    first_data["results"][0]["id"] = 1000000001
    first_data["results"][1]["id"] = 1000000002
    first_data["pagination"] = {"limit": 2, "total": 3}
    first_fixture = {**search_fixture, "data": first_data}

    second_data = deepcopy(first_data)
    duplicate = deepcopy(first_data["results"][1])
    third = deepcopy(first_data["results"][0])
    third["id"] = 1000000003
    second_data["results"] = [duplicate, third]
    second_fixture = {**search_fixture, "data": second_data}

    paths = {
        1000000001: "/detail/prodej/dum/chata/a/1000000001",
        1000000002: "/detail/prodej/dum/chata/b/1000000002",
        1000000003: "/detail/prodej/dum/chata/c/1000000003",
    }
    search_pages = {
        1: next_data_html(first_fixture, page=1, links=list(paths.items())[:2]),
        2: next_data_html(second_fixture, page=2, links=list(paths.items())[1:]),
    }
    detail_fixture = load_fixture("detail_chata.json")
    client = FakeClient(search_pages, next_data_html(detail_fixture))

    fetched = list(SrealityListingSource(client).iter_kind(ListingKind.CHATA))

    assert [item.detail.sreality_id for item in fetched] == [1000000001, 1000000002, 1000000003]
    assert client.search_calls == [(ListingKind.CHATA, 1), (ListingKind.CHATA, 2)]
    assert client.detail_calls == list(paths.values())


def test_source_uses_search_data_after_detail_consent_redirect() -> None:
    search_fixture = load_fixture("search_chata.json")
    search_data = deepcopy(search_fixture["data"])
    search_data["results"][0]["id"] = 1000000001
    search_data["results"][1]["id"] = 1000000002
    search_data["pagination"] = {"limit": 2, "total": 2}
    fixture = {**search_fixture, "data": search_data}
    ids = [item["id"] for item in search_data["results"]]
    paths = [f"/detail/prodej/dum/chata/example/{listing_id}" for listing_id in ids]
    page = next_data_html(fixture, page=1, links=list(zip(ids, paths, strict=True)))
    client = FakeClient(
        {1: page},
        "",
        detail_error=ResponseValidationError(
            "response attempted to redirect outside the allowed HTTPS hosts"
        ),
    )
    logger = Mock()

    fetched = list(SrealityListingSource(client, logger=logger).iter_kind(ListingKind.CHATA))

    assert [item.detail.sreality_id for item in fetched] == ids
    assert client.detail_calls == [paths[0]]
    assert fetched[0].detail.name == search_data["results"][0]["name"]
    assert fetched[0].detail.locality.latitude is not None
    assert fetched[0].detail.description is None
    assert fetched[0].detail.params == {}
    logger.warning.assert_called_once()
