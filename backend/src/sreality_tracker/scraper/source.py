"""Paginated Sreality source adapter for the persistence pipeline."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from sreality_tracker.domain.listings import ListingDetail, ListingKind, SearchListing
from sreality_tracker.scraper.client import (
    SITE_BASE_URL,
    ResponseValidationError,
)
from sreality_tracker.scraper.parser import (
    ParseError,
    extract_detail_paths_html,
    parse_detail_html,
    parse_search_html,
)


class ListingSourceError(RuntimeError):
    """Raised when a search result cannot be resolved to a detail payload."""


@dataclass(frozen=True, slots=True)
class FetchedListing:
    detail: ListingDetail


class ListingSource(Protocol):
    def iter_kind(self, kind: ListingKind) -> Iterator[FetchedListing]: ...


class _SrealityClientLike(Protocol):
    def fetch_search_page(self, kind: ListingKind, page: int = 1) -> str: ...

    def fetch_detail_page(self, detail_path: str) -> str: ...


class SrealityListingSource:
    """Traverse every advertised search page and fetch each unique detail."""

    def __init__(
        self, client: _SrealityClientLike, *, logger: logging.Logger | None = None
    ) -> None:
        self._client = client
        self._logger = logger or logging.getLogger("sreality_tracker.scraper.source")

    def iter_kind(self, kind: ListingKind) -> Iterator[FetchedListing]:
        page_number = 1
        total_pages: int | None = None
        seen_ids: set[int] = set()
        detail_pages_available = True

        while total_pages is None or page_number <= total_pages:
            html = self._client.fetch_search_page(kind, page_number)
            page = parse_search_html(html, kind)
            if page.page != page_number:
                raise ListingSourceError(
                    f"search returned page {page.page} while page {page_number} was requested"
                )
            if page.limit <= 0:
                raise ListingSourceError("search returned a non-positive page limit")
            current_total_pages = max(1, (page.total + page.limit - 1) // page.limit)
            if total_pages is None:
                total_pages = current_total_pages
            else:
                total_pages = max(total_pages, current_total_pages)

            detail_paths = extract_detail_paths_html(html)
            for search_listing in page.listings:
                if search_listing.sreality_id in seen_ids:
                    continue
                detail_path = detail_paths.get(search_listing.sreality_id)
                if detail_path is None:
                    raise ListingSourceError(
                        f"search page has no detail link for listing {search_listing.sreality_id}"
                    )
                source_url = f"{SITE_BASE_URL}{detail_path}"
                detail = None
                if detail_pages_available:
                    try:
                        detail_html = self._client.fetch_detail_page(detail_path)
                        detail = parse_detail_html(
                            detail_html,
                            sreality_id=search_listing.sreality_id,
                            source_url=source_url,
                            expected_kind=kind,
                        )
                    except (ResponseValidationError, ParseError) as error:
                        detail_pages_available = False
                        self._logger.warning(
                            "Sreality detail pages are unavailable; using search result data",
                            extra={
                                "event": "detail_fallback",
                                "step": type(error).__name__,
                            },
                        )
                if detail is None:
                    detail = _detail_from_search(search_listing, source_url=source_url)
                seen_ids.add(search_listing.sreality_id)
                yield FetchedListing(detail=detail)

            page_number += 1

        self._logger.info(
            "Sreality category scrape completed",
            extra={
                "event": "category_scrape_completed",
                "step": "complete",
                "kind": kind.value,
                "found_count": len(seen_ids),
            },
        )


def _detail_from_search(search: SearchListing, *, source_url: str) -> ListingDetail:
    """Build a deliberately incomplete detail when public detail SSR is unavailable."""
    return ListingDetail(
        sreality_id=search.sreality_id,
        kind=search.kind,
        source_url=source_url,
        name=search.name,
        description=None,
        price_note=None,
        price=search.price,
        locality=search.locality,
        usable_area_m2=None,
        land_area_m2=None,
        building_area_m2=None,
        floor_area_m2=None,
        garden_area_m2=None,
        building_condition_code=None,
        building_type_code=None,
        object_type_code=None,
        room_count_code=None,
        energy_rating_code=None,
        images=search.images,
        params={},
        raw=search.raw,
    )
