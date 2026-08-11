"""Paginated Sreality source adapter for the persistence pipeline."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from sreality_tracker.domain.listings import ListingDetail, ListingKind
from sreality_tracker.scraper.client import SITE_BASE_URL
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

    def __init__(self, client: _SrealityClientLike) -> None:
        self._client = client

    def iter_kind(self, kind: ListingKind) -> Iterator[FetchedListing]:
        page_number = 1
        total_pages: int | None = None
        seen_ids: set[int] = set()

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
                detail_html = self._client.fetch_detail_page(detail_path)
                try:
                    detail = parse_detail_html(
                        detail_html,
                        sreality_id=search_listing.sreality_id,
                        source_url=f"{SITE_BASE_URL}{detail_path}",
                        expected_kind=kind,
                    )
                except ParseError as error:
                    raise ListingSourceError(
                        f"invalid detail payload for listing {search_listing.sreality_id}"
                    ) from error
                seen_ids.add(search_listing.sreality_id)
                yield FetchedListing(detail=detail)

            page_number += 1
