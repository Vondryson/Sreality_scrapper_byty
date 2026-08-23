"""Capture small, aggressively sanitized Sreality SSR fixtures.

This is an explicit M0 discovery tool, not the production scraper. All string
values and identifying numeric fields are replaced before files are written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from scripts.validate_sreality_api import (
    CATEGORIES,
    SITE_BASE_URL,
    PageProbe,
    ValidationError,
    get_search_state,
    parse_next_data,
)

ANONYMIZED_TEXT = "<anonymized>"
ANONYMIZED_URL = "https://example.invalid/fixture"
ANONYMIZED_ID = 1_000_000_001
ANONYMIZED_PRICE = 1_234_567
ANONYMIZED_AREA = 100
ANONYMIZED_LATITUDE = 50.0
ANONYMIZED_LONGITUDE = 14.0
SOURCE_DOMAIN_PATTERN = re.compile(r"(?:sreality\.cz|sdn\.cz|seznam\.cz)", re.IGNORECASE)


class DetailLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and href.startswith("/detail/") and href not in self.links:
            self.links.append(href)


def is_identifier_key(key: str) -> bool:
    lowered = key.lower()
    return lowered == "id" or lowered.endswith("id") or lowered.endswith("_id")


def sanitize_scalar(value: Any, key: str) -> Any:
    lowered = key.lower()
    if isinstance(value, str):
        if "url" in lowered or "href" in lowered or "link" in lowered:
            return ANONYMIZED_URL
        return ANONYMIZED_TEXT
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        if is_identifier_key(key):
            return ANONYMIZED_ID
        if "latitude" in lowered or lowered in {"lat", "gpslat"}:
            return ANONYMIZED_LATITUDE
        if "longitude" in lowered or lowered in {"lon", "lng", "gpslon"}:
            return ANONYMIZED_LONGITUDE
        if "price" in lowered:
            return ANONYMIZED_PRICE
        if "area" in lowered or "plocha" in lowered:
            return ANONYMIZED_AREA
    return value


def sanitize(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {
            str(child_key): sanitize(child, str(child_key)) for child_key, child in value.items()
        }
    if isinstance(value, list):
        limit = 2 if key in {"results", "images", "nearest", "extendedPois", "videos"} else None
        selected = value[:limit] if limit is not None else value
        return [sanitize(child, key) for child in selected]
    return sanitize_scalar(value, key)


def find_detail_link(html: str, external_id: str) -> str:
    parser = DetailLinkParser()
    parser.feed(html)
    suffix = f"/{external_id}"
    for link in parser.links:
        if link.endswith(suffix):
            return link
    raise ValidationError("No matching detail link found on search page")


def extract_search_fixture(next_data: dict[str, Any], category_label: str) -> dict[str, Any]:
    _, search = get_search_state(next_data)
    params = dict(search["params"])
    params.pop("timestamp", None)
    data = search["data"]
    selected_data = {
        "pagination": data.get("pagination"),
        "results": data.get("results", [])[:2],
        "warnings": data.get("warnings"),
    }
    return {
        "fixture_meta": fixture_meta(category_label, "search"),
        "query_name": "estatesSearch",
        "query_params": sanitize(params),
        "data": sanitize(selected_data),
    }


def extract_detail_fixture(next_data: dict[str, Any], category_label: str) -> dict[str, Any]:
    estate = get_estate_data(next_data)
    return {
        "fixture_meta": fixture_meta(category_label, "detail"),
        "query_name": "estate",
        "data": sanitize(estate),
    }


def get_estate_data(next_data: dict[str, Any]) -> dict[str, Any]:
    try:
        queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]
    except (KeyError, TypeError) as error:
        raise ValidationError("Detail page has no dehydrated queries") from error

    for query in queries:
        query_key = query.get("queryKey") if isinstance(query, dict) else None
        query_name = query_key[0] if isinstance(query_key, list) and query_key else query_key
        if query_name == "estate":
            try:
                estate = query["state"]["data"]
            except (KeyError, TypeError) as error:
                raise ValidationError("Invalid estate query state") from error
            if not isinstance(estate, dict):
                raise ValidationError("Estate query data is not an object")
            return estate
    raise ValidationError("No estate query found on detail page")


def fixture_meta(category_label: str, fixture_type: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "captured_on": "2026-08-02",
        "category": category_label,
        "fixture_type": fixture_type,
        "source_contract": "Next.js __NEXT_DATA__ SSR",
        "sanitized": True,
        "contains_original_listing_content": False,
    }


def make_missing_optional_fixture(detail: dict[str, Any]) -> dict[str, Any]:
    edge = json.loads(json.dumps(detail))
    if not isinstance(edge, dict):
        raise ValidationError("Detail fixture is not an object")
    edge["fixture_meta"] = fixture_meta("chata", "detail_missing_optional")
    data = edge.get("data")
    if not isinstance(data, dict):
        raise ValidationError("Detail fixture data is not an object")
    for key in ("note", "images", "matterportUrl", "panorama", "seller", "videos"):
        data.pop(key, None)
    data["description"] = None
    data["estateArea"] = None
    return edge


def assert_sanitized(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    if SOURCE_DOMAIN_PATTERN.search(serialized):
        raise ValidationError("Sanitized fixture still contains a source domain")
    if "@" in serialized:
        raise ValidationError("Sanitized fixture may still contain an email address")


def write_fixture(output_dir: Path, name: str, payload: dict[str, Any]) -> None:
    assert_sanitized(payload)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (output_dir / name).write_text(serialized, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.delay_seconds < 0.5:
        print("Refusing delay below 0.5 seconds.", file=sys.stderr)
        return 2

    probe = PageProbe(args.delay_seconds, args.timeout_seconds)
    captured: dict[str, dict[str, Any]] = {}
    try:
        for category in CATEGORIES:
            search_html = probe.get_html(category.page_url(1))
            search_next_data = parse_next_data(search_html)
            _, search = get_search_state(search_next_data)
            results = search["data"].get("results")
            if not isinstance(results, list) or not results or not isinstance(results[0], dict):
                raise ValidationError(f"No search result available for {category.label}")
            external_id = str(results[0].get("id"))
            detail_path = find_detail_link(search_html, external_id)
            detail_next_data = probe.get_next_data(SITE_BASE_URL + detail_path)

            captured[f"search_{category.label}.json"] = extract_search_fixture(
                search_next_data, category.label
            )
            captured[f"detail_{category.label}.json"] = extract_detail_fixture(
                detail_next_data, category.label
            )
    except ValidationError as error:
        print(f"Capture failed after {probe.request_count} requests: {error}", file=sys.stderr)
        return 1

    captured["detail_missing_optional.json"] = make_missing_optional_fixture(
        captured["detail_chata.json"]
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in captured.items():
        write_fixture(args.output_dir, filename, payload)

    print(f"Wrote {len(captured)} sanitized fixtures after {probe.request_count} requests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
