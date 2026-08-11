"""Listing collection API routes."""

from typing import Annotated

from fastapi import APIRouter, Query

from sreality_tracker.api.dependencies import DatabaseSession
from sreality_tracker.api.listing_contracts import ListingFilters, ListingPage
from sreality_tracker.api.listing_repository import list_listings

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("", response_model=ListingPage)
def listing_collection(
    session: DatabaseSession,
    filters: Annotated[ListingFilters, Query()],
) -> ListingPage:
    return list_listings(session, filters)
