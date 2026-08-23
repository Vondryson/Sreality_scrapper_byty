"""Perform a small, read-only validation of current Sreality search pages.

The legacy JSON API used by the 2024 scraper returns HTTP 404 as of 2026-08-02.
Current search pages expose structured search results in the Next.js
``__NEXT_DATA__`` SSR payload. This script validates that public contract while
storing only aggregate metadata and hashes of external listing IDs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

SITE_BASE_URL = "https://www.sreality.cz"
USER_AGENT = "SrealityChatyTracker/0.1 validation (+private research project)"
DEFAULT_DELAY_SECONDS = 0.75
DEFAULT_TIMEOUT_SECONDS = 20.0


class ValidationError(RuntimeError):
    """Raised when a public page does not satisfy an expected invariant."""


@dataclass(frozen=True)
class Category:
    label: str
    slug: str
    subtype: int

    def page_url(self, page: int) -> str:
        base = f"{SITE_BASE_URL}/hledani/prodej/domy/{self.slug}"
        return base if page == 1 else f"{base}?{urlencode({'strana': page})}"


CATEGORIES = (
    Category(label="chata", slug="chaty", subtype=33),
    Category(label="chalupa", slug="chalupy", subtype=43),
)


class NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._inside_next_data = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attributes = dict(attrs)
        self._inside_next_data = attributes.get("id") == "__NEXT_DATA__"

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inside_next_data:
            self._inside_next_data = False

    def handle_data(self, data: str) -> None:
        if self._inside_next_data:
            self._chunks.append(data)

    def payload(self) -> dict[str, Any]:
        if not self._chunks:
            raise ValidationError("Page does not contain __NEXT_DATA__")
        try:
            value = json.loads("".join(self._chunks))
        except json.JSONDecodeError as error:
            raise ValidationError("__NEXT_DATA__ is not valid JSON") from error
        if not isinstance(value, dict):
            raise ValidationError("__NEXT_DATA__ must be a JSON object")
        return value


class PageProbe:
    def __init__(self, delay_seconds: float, timeout_seconds: float) -> None:
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.request_count = 0
        curl_path = shutil.which("curl")
        if curl_path is None:
            raise ValidationError("curl is required for the discovery probe")
        self.curl_path = curl_path

    def get_html(self, url: str) -> str:
        if self.request_count:
            time.sleep(self.delay_seconds)
        self.request_count += 1

        command = [
            self.curl_path,
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time",
            str(self.timeout_seconds),
            "--user-agent",
            USER_AGENT,
            url,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                encoding="utf-8",
                timeout=self.timeout_seconds + 5,
            )
        except subprocess.TimeoutExpired as error:
            raise ValidationError(f"curl timed out while requesting {url}") from error

        if result.returncode != 0:
            message = result.stderr.strip() or f"curl exit code {result.returncode}"
            raise ValidationError(f"Failed to request {url}: {message}")

        return result.stdout

    def get_next_data(self, url: str) -> dict[str, Any]:
        return parse_next_data(self.get_html(url))

    def download_size(self, url: str) -> int | None:
        if self.request_count:
            time.sleep(self.delay_seconds)
        self.request_count += 1
        command = [
            self.curl_path,
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time",
            str(self.timeout_seconds),
            "--output",
            os.devnull,
            "--write-out",
            "%{size_download}",
            "--user-agent",
            USER_AGENT,
            url,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                encoding="utf-8",
                timeout=self.timeout_seconds + 5,
            )
        except subprocess.TimeoutExpired:
            return None
        if result.returncode != 0:
            return None
        try:
            return int(float(result.stdout.strip()))
        except ValueError:
            return None


def parse_next_data(html: str) -> dict[str, Any]:
    parser = NextDataParser()
    parser.feed(html)
    return parser.payload()


def get_search_state(next_data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        page_props = next_data["props"]["pageProps"]
        queries = page_props["dehydratedState"]["queries"]
    except (KeyError, TypeError) as error:
        raise ValidationError("Next.js payload has no dehydrated search state") from error

    if not isinstance(page_props, dict) or not isinstance(queries, list):
        raise ValidationError("Invalid pageProps or dehydrated queries")

    for query in queries:
        if not isinstance(query, dict):
            continue
        query_key = query.get("queryKey")
        if isinstance(query_key, list) and query_key and query_key[0] == "estatesSearch":
            try:
                params = query_key[1]
                search_data = query["state"]["data"]
            except (IndexError, KeyError, TypeError) as error:
                raise ValidationError("Invalid estatesSearch query structure") from error
            if isinstance(params, dict) and isinstance(search_data, dict):
                return page_props, {"params": params, "data": search_data}

    raise ValidationError("No estatesSearch query found in SSR payload")


def get_listing_ids(results: Any) -> list[str]:
    if not isinstance(results, list) or not all(isinstance(item, dict) for item in results):
        raise ValidationError("Search results must be a list of objects")

    ids: list[str] = []
    for listing in results:
        external_id = listing.get("id")
        if external_id is None:
            raise ValidationError("Search result is missing id")
        ids.append(str(external_id))
    if len(ids) != len(set(ids)):
        raise ValidationError("Search page contains duplicate IDs")
    return ids


def get_codebook_value(value: Any, field: str) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        nested = value.get("value")
        if isinstance(nested, int):
            return nested
    raise ValidationError(f"Search result has invalid {field} codebook value")


def hash_ids(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode()).hexdigest()


def extract_page(
    next_data: dict[str, Any], category: Category, expected_page: int
) -> dict[str, Any]:
    page_props, search = get_search_state(next_data)
    params = search["params"]
    data = search["data"]

    expected_filters = {
        "categoryTypeCb": [1],
        "categoryMainCb": [2],
        "categorySubCb": [category.subtype],
    }
    for key, expected in expected_filters.items():
        if params.get(key) != expected:
            raise ValidationError(f"Unexpected {key} for {category.label}: {params.get(key)!r}")
    if params.get("page") != expected_page:
        raise ValidationError(
            f"Expected page {expected_page} for {category.label}, got {params.get('page')!r}"
        )

    limit = params.get("limit")
    total = page_props.get("total")
    results = data.get("results")
    if not isinstance(limit, int) or limit <= 0:
        raise ValidationError("Search query has no positive page limit")
    if not isinstance(total, int) or total <= 0:
        raise ValidationError(f"Filtered total for {category.label} is not positive")

    ids = get_listing_ids(results)
    if len(ids) > limit:
        raise ValidationError("Search returned more results than its declared limit")
    for listing in results:
        observed = (
            get_codebook_value(listing.get("categoryTypeCb"), "categoryTypeCb"),
            get_codebook_value(listing.get("categoryMainCb"), "categoryMainCb"),
            get_codebook_value(listing.get("categorySubCb"), "categorySubCb"),
        )
        if observed != (1, 2, category.subtype):
            raise ValidationError(f"Result category mismatch for {category.label}: {observed!r}")

    return {
        "build_id": next_data.get("buildId"),
        "total": total,
        "page": expected_page,
        "limit": limit,
        "returned": len(ids),
        "ids": ids,
    }


def validate_category(probe: PageProbe, category: Category) -> dict[str, Any]:
    first = extract_page(probe.get_next_data(category.page_url(1)), category, 1)
    repeated = extract_page(probe.get_next_data(category.page_url(1)), category, 1)
    second = extract_page(probe.get_next_data(category.page_url(2)), category, 2)

    if first["ids"] != repeated["ids"]:
        raise ValidationError(f"Repeated first page is not stable for {category.label}")
    if set(first["ids"]) & set(second["ids"]):
        raise ValidationError(f"Pages 1 and 2 overlap for {category.label}")
    if first["limit"] != second["limit"] or first["limit"] != repeated["limit"]:
        raise ValidationError(f"Page limit changed during validation for {category.label}")
    if first["total"] != second["total"] or first["total"] != repeated["total"]:
        raise ValidationError(f"Filtered total changed during validation for {category.label}")
    if first["returned"] != min(first["total"], first["limit"]):
        raise ValidationError(f"First page size is inconsistent for {category.label}")

    return {
        "label": category.label,
        "slug": category.slug,
        "filter": {
            "category_type_cb": 1,
            "category_main_cb": 2,
            "category_sub_cb": category.subtype,
        },
        "filtered_total": first["total"],
        "observed_page_limit": first["limit"],
        "page_1_returned": first["returned"],
        "page_2_returned": second["returned"],
        "page_1_repeat_is_stable": True,
        "page_1_id_hash": hash_ids(first["ids"]),
        "page_1_repeat_id_hash": hash_ids(repeated["ids"]),
        "page_2_id_hash": hash_ids(second["ids"]),
        "page_overlap_count": 0,
        "next_build_id": first["build_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path for the aggregate JSON validation report.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Delay between requests (default: {DEFAULT_DELAY_SECONDS}).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout (default: {DEFAULT_TIMEOUT_SECONDS}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.delay_seconds < 0.5:
        print("Refusing delay below 0.5 seconds.", file=sys.stderr)
        return 2
    if args.timeout_seconds <= 0:
        print("Timeout must be positive.", file=sys.stderr)
        return 2

    started_at = datetime.now(UTC)
    try:
        probe = PageProbe(args.delay_seconds, args.timeout_seconds)
        categories = [validate_category(probe, category) for category in CATEGORIES]
    except ValidationError as error:
        count = probe.request_count if "probe" in locals() else 0
        print(f"Validation failed after {count} requests: {error}", file=sys.stderr)
        return 1

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round((datetime.now(UTC) - started_at).total_seconds(), 3),
        "source": "public Next.js __NEXT_DATA__ SSR payload",
        "site_base_url": SITE_BASE_URL,
        "legacy_api_status": "HTTP 404 observed for /api/cs/v2/estates and /count",
        "request_count": probe.request_count,
        "delay_seconds": args.delay_seconds,
        "stores_personal_or_listing_content": False,
        "categories": categories,
        "validation_passed": True,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(serialized_report, encoding="utf-8")
    print(f"Validation passed with {probe.request_count} requests. Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
