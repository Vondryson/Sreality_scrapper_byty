"""Build an aggregate data and image profile from a small live sample.

No listing text, contact data, IDs, exact locations, image URLs, or image bytes
are persisted. The default sample performs 22 delayed read-only requests:
two search pages, ten detail pages, and at most ten image downloads.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.capture_sreality_fixtures import find_detail_link, get_estate_data
from scripts.validate_sreality_api import (
    CATEGORIES,
    PageProbe,
    SITE_BASE_URL,
    ValidationError,
    get_search_state,
    parse_next_data,
)

DEFAULT_SAMPLE_PER_CATEGORY = 5
MAX_SAMPLE_PER_CATEGORY = 10
IMAGE_TRANSFORMATION = "fl=res,800,600,3|shr,,20|webp,60"


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def normalize_url(url: str) -> str:
    return "https:" + url if url.startswith("//") else url


def image_variant_url(url: str) -> str:
    normalized = normalize_url(url)
    separator = "&" if "?" in normalized else "?"
    return f"{normalized}{separator}{IMAGE_TRANSFORMATION}"


def observe_fields(
    observations: dict[str, dict[str, Any]], mapping: dict[str, Any]
) -> None:
    for key, value in mapping.items():
        field = observations.setdefault(
            key,
            {"present": 0, "non_null": 0, "types": Counter()},
        )
        field["present"] += 1
        if value is not None:
            field["non_null"] += 1
        field["types"][type_name(value)] += 1


def finalize_fields(
    observations: dict[str, dict[str, Any]], sample_size: int
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(observations):
        field = observations[key]
        result[key] = {
            "present": field["present"],
            "missing": sample_size - field["present"],
            "non_null": field["non_null"],
            "null": field["present"] - field["non_null"],
            "types": dict(sorted(field["types"].items())),
        }
    return result


def numeric_summary(values: list[int | float], sample_size: int) -> dict[str, Any]:
    if not values:
        return {"observed": 0, "missing_or_non_numeric": sample_size}
    return {
        "observed": len(values),
        "missing_or_non_numeric": sample_size - len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def collect_numeric(mapping: dict[str, Any], key: str, target: list[int | float]) -> None:
    value = mapping.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        target.append(value)


def build_profile(
    probe: PageProbe, sample_per_category: int
) -> dict[str, Any]:
    top_level_fields: dict[str, dict[str, Any]] = {}
    param_fields: dict[str, dict[str, Any]] = {}
    category_counts: Counter[str] = Counter()
    prices_czk: list[int | float] = []
    prices_per_sqm: list[int | float] = []
    estate_areas: list[int | float] = []
    usable_areas: list[int | float] = []
    building_areas: list[int | float] = []
    image_counts: list[int] = []
    image_widths: list[int | float] = []
    image_heights: list[int | float] = []
    image_download_sizes: list[int | float] = []
    image_domains: Counter[str] = Counter()
    image_download_failures = 0
    sampled_details = 0

    for category in CATEGORIES:
        search_html = probe.get_html(category.page_url(1))
        search_next_data = parse_next_data(search_html)
        _, search = get_search_state(search_next_data)
        results = search["data"].get("results")
        if not isinstance(results, list):
            raise ValidationError(f"No result list for {category.label}")

        selected = [item for item in results if isinstance(item, dict)][
            :sample_per_category
        ]
        if len(selected) < sample_per_category:
            raise ValidationError(f"Insufficient sample for {category.label}")

        for result in selected:
            external_id = str(result.get("id"))
            detail_path = find_detail_link(search_html, external_id)
            estate = get_estate_data(probe.get_next_data(SITE_BASE_URL + detail_path))
            sampled_details += 1
            category_counts[category.label] += 1
            observe_fields(top_level_fields, estate)

            params = estate.get("params")
            if isinstance(params, dict):
                observe_fields(param_fields, params)
                collect_numeric(params, "usableArea", usable_areas)
                collect_numeric(params, "buildingArea", building_areas)

            collect_numeric(estate, "priceCzk", prices_czk)
            collect_numeric(estate, "priceCzkPerSqM", prices_per_sqm)
            collect_numeric(estate, "estateArea", estate_areas)

            images = estate.get("images")
            if not isinstance(images, list):
                image_counts.append(0)
                continue
            image_counts.append(len(images))
            for image in images:
                if not isinstance(image, dict):
                    continue
                collect_numeric(image, "width", image_widths)
                collect_numeric(image, "height", image_heights)
                url = image.get("url")
                if isinstance(url, str):
                    normalized_url = normalize_url(url)
                    domain = urlparse(normalized_url).hostname
                    if domain:
                        image_domains[domain] += 1

            first_image = next(
                (
                    image.get("url")
                    for image in images
                    if isinstance(image, dict) and isinstance(image.get("url"), str)
                ),
                None,
            )
            if isinstance(first_image, str):
                downloaded_size = probe.download_size(image_variant_url(first_image))
                if downloaded_size is None:
                    image_download_failures += 1
                else:
                    image_download_sizes.append(downloaded_size)

    return {
        "sample": {
            "details_total": sampled_details,
            "details_by_category": dict(sorted(category_counts.items())),
            "sampling_method": "first N newest results from page 1 per category",
            "limitations": [
                "Small non-random sample; results are directional, not population estimates.",
                "One image per sampled listing was downloaded only to measure bytes.",
            ],
        },
        "top_level_fields": finalize_fields(top_level_fields, sampled_details),
        "params_fields": finalize_fields(param_fields, sampled_details),
        "numeric_variants": {
            "priceCzk": numeric_summary(prices_czk, sampled_details),
            "priceCzkPerSqM": numeric_summary(prices_per_sqm, sampled_details),
            "estateArea": numeric_summary(estate_areas, sampled_details),
            "params.usableArea": numeric_summary(usable_areas, sampled_details),
            "params.buildingArea": numeric_summary(building_areas, sampled_details),
        },
        "images": {
            "count_per_listing": numeric_summary(image_counts, sampled_details),
            "declared_width": numeric_summary(image_widths, len(image_widths)),
            "declared_height": numeric_summary(image_heights, len(image_heights)),
            "downloaded_file_bytes": numeric_summary(
                image_download_sizes, sampled_details
            ),
            "download_failures": image_download_failures,
            "measured_variant": "800x600 WebP quality 60 as rendered by the search page",
            "observed_domains": dict(sorted(image_domains.items())),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--sample-per-category",
        type=int,
        default=DEFAULT_SAMPLE_PER_CATEGORY,
    )
    parser.add_argument("--delay-seconds", type=float, default=0.75)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.sample_per_category <= MAX_SAMPLE_PER_CATEGORY:
        print(
            f"sample-per-category must be between 1 and {MAX_SAMPLE_PER_CATEGORY}",
            file=sys.stderr,
        )
        return 2
    if args.delay_seconds < 0.5:
        print("Refusing delay below 0.5 seconds.", file=sys.stderr)
        return 2

    started_at = datetime.now(UTC)
    probe = PageProbe(args.delay_seconds, args.timeout_seconds)
    try:
        profile = build_profile(probe, args.sample_per_category)
    except ValidationError as error:
        print(f"Profiling failed after {probe.request_count} requests: {error}", file=sys.stderr)
        return 1

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "duration_seconds": round((datetime.now(UTC) - started_at).total_seconds(), 3),
        "request_count": probe.request_count,
        "delay_seconds": args.delay_seconds,
        "stores_listing_content_or_image_urls": False,
        **profile,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(serialized, encoding="utf-8")
    print(f"Profile completed with {probe.request_count} requests. Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
