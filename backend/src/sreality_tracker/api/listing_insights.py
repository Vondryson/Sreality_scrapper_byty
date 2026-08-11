"""Routes for listing detail, history, map data, and price medians."""

from typing import Annotated

from fastapi import APIRouter, Query

from sreality_tracker.api.dependencies import DatabaseSession
from sreality_tracker.api.listing_contracts import ListingFilters
from sreality_tracker.api.listing_insight_contracts import (
    ListingDetailResponse,
    ListingHistoryResponse,
    MapListingResponse,
    PriceMedianResponse,
)
from sreality_tracker.api.listing_insight_repository import (
    get_listing_detail,
    get_listing_history,
    get_price_medians,
    list_map_listings,
)

router = APIRouter(tags=["listings"])


@router.get("/listings/{listing_id}", response_model=ListingDetailResponse)
def listing_detail(listing_id: int, session: DatabaseSession) -> ListingDetailResponse:
    return get_listing_detail(session, listing_id)


@router.get("/listings/{listing_id}/history", response_model=ListingHistoryResponse)
def listing_history(listing_id: int, session: DatabaseSession) -> ListingHistoryResponse:
    return get_listing_history(session, listing_id)


@router.get("/map/listings", response_model=MapListingResponse)
def map_listings(
    session: DatabaseSession,
    filters: Annotated[ListingFilters, Query()],
) -> MapListingResponse:
    return list_map_listings(session, filters)


@router.get("/analytics/price-medians", response_model=PriceMedianResponse)
def price_medians(
    session: DatabaseSession,
    filters: Annotated[ListingFilters, Query()],
) -> PriceMedianResponse:
    return get_price_medians(session, filters)
