"""Owner-only routes for favorites, private notes, and image archival."""

from fastapi import APIRouter, Request

from sreality_tracker.api.dependencies import DatabaseSession
from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.owner import AuthenticatedOwner
from sreality_tracker.api.user_listing_contracts import (
    UserListingResponse,
    UserListingUpdate,
)
from sreality_tracker.api.user_listing_service import ImageArchiver, update_user_listing

router = APIRouter(prefix="/listings", tags=["listings"])


@router.patch("/{listing_id}/user-data", response_model=UserListingResponse)
def patch_user_listing(
    listing_id: int,
    update: UserListingUpdate,
    session: DatabaseSession,
    _owner: AuthenticatedOwner,
    request: Request,
) -> UserListingResponse:
    archiver: ImageArchiver | None = request.app.state.container.image_archiver
    if archiver is None:
        raise ApiError(
            status_code=503,
            code="image_archive_unavailable",
            message="Image archive is unavailable",
        )
    return update_user_listing(
        session,
        listing_id=listing_id,
        update=update,
        archiver=archiver,
    )
