"""Owner-only routes for favorites, private notes, and image archival."""

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from sreality_tracker.api.dependencies import DatabaseSession
from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.owner import AuthenticatedOwner
from sreality_tracker.api.user_listing_contracts import (
    UserListingResponse,
    UserListingUpdate,
)
from sreality_tracker.api.user_listing_service import ImageArchiver, update_user_listing
from sreality_tracker.db.models import ListingImage
from sreality_tracker.storage.images import ImageArchiveError

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("/{listing_id}/images/{position}/archive", response_class=Response)
def archived_listing_image(
    listing_id: int,
    position: int,
    session: DatabaseSession,
    _owner: AuthenticatedOwner,
    request: Request,
) -> Response:
    object_key = session.scalar(
        select(ListingImage.archive_object_key).where(
            ListingImage.listing_id == listing_id,
            ListingImage.position == position,
            ListingImage.archive_object_key.is_not(None),
        ).order_by(ListingImage.id).limit(1)
    )
    archiver: ImageArchiver | None = request.app.state.container.image_archiver
    if object_key is None or archiver is None:
        raise ApiError(status_code=404, code="archived_image_not_found", message="Image not found")
    try:
        image = archiver.storage.load(key=object_key)
    except (ImageArchiveError, OSError, ValueError) as error:
        raise ApiError(
            status_code=404,
            code="archived_image_not_found",
            message="Image not found",
        ) from error
    return Response(
        content=image.content,
        media_type=image.content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


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
