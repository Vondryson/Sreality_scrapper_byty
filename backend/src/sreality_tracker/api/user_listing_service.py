"""Idempotent private listing updates and resilient favorite image archival."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.user_listing_contracts import (
    UserListingResponse,
    UserListingUpdate,
)
from sreality_tracker.db.models import (
    ImageArchiveStatus,
    Listing,
    ListingImage,
    UserListingData,
)
from sreality_tracker.storage.images import (
    ImageArchiveError,
    ImageArchiveStorage,
    ImageFetcher,
    image_archive_key,
)


@dataclass(frozen=True, slots=True)
class ImageArchiver:
    fetcher: ImageFetcher
    storage: ImageArchiveStorage


def update_user_listing(
    session: Session,
    *,
    listing_id: int,
    update: UserListingUpdate,
    archiver: ImageArchiver,
) -> UserListingResponse:
    if session.scalar(select(Listing.id).where(Listing.id == listing_id)) is None:
        raise ApiError(status_code=404, code="listing_not_found", message="Listing not found")
    user_data = session.get(UserListingData, listing_id)
    if user_data is None:
        user_data = UserListingData(listing_id=listing_id, is_favorite=False)
        session.add(user_data)
    if "is_favorite" in update.model_fields_set:
        user_data.is_favorite = bool(update.is_favorite)
    if "private_note" in update.model_fields_set:
        user_data.private_note = update.private_note
    user_data.updated_at = func.now()
    session.commit()

    if user_data.is_favorite:
        _archive_listing_images(session, listing_id=listing_id, archiver=archiver)
    archived, failed = session.execute(
        select(
            func.count().filter(ListingImage.archive_status == ImageArchiveStatus.ARCHIVED),
            func.count().filter(ListingImage.archive_status == ImageArchiveStatus.FAILED),
        ).where(ListingImage.listing_id == listing_id)
    ).one()
    session.refresh(user_data)
    return UserListingResponse(
        listing_id=listing_id,
        is_favorite=user_data.is_favorite,
        private_note=user_data.private_note,
        archived_images=int(archived),
        failed_images=int(failed),
    )


def _archive_listing_images(
    session: Session, *, listing_id: int, archiver: ImageArchiver
) -> None:
    images = session.scalars(
        select(ListingImage)
        .where(ListingImage.listing_id == listing_id)
        .order_by(ListingImage.position, ListingImage.id)
    ).all()
    for image in images:
        if image.archive_status is ImageArchiveStatus.ARCHIVED:
            continue
        image.archive_status = ImageArchiveStatus.PENDING
        image.last_error = None
        session.commit()
        try:
            fetched = archiver.fetcher.fetch(image.source_url)
            stored = archiver.storage.store(
                key=image_archive_key(
                    listing_id=listing_id,
                    source_fingerprint=image.source_fingerprint,
                ),
                image=fetched,
            )
        except (ImageArchiveError, OSError, ValueError) as error:
            image.archive_status = ImageArchiveStatus.FAILED
            image.last_error = type(error).__name__
            session.commit()
            continue
        image.archive_object_key = stored.key
        image.content_hash = stored.sha256
        image.archive_status = ImageArchiveStatus.ARCHIVED
        image.last_error = None
        session.commit()
