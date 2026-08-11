"""Idempotent persistence for locally calculated listing distances."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from sreality_tracker.db.models import Listing, ListingDistance
from sreality_tracker.distances.air import Coordinates, haversine_distance_km, optional_coordinates
from sreality_tracker.domain.reference_points import PRAGUE_CENTER_V1, ReferencePoint

LOCAL_PROVIDER = "local_haversine"
STRAIGHT_LINE_MODE = "straight_line"
DISTANCE_PRECISION_KM = Decimal("0.001")


def ensure_air_distance(
    session: Session,
    *,
    listing: Listing,
    calculated_at: datetime,
    reference: ReferencePoint = PRAGUE_CENTER_V1,
) -> ListingDistance | None:
    """Create one cached air-distance row when the listing has valid paired GPS."""
    target = optional_coordinates(listing.latitude, listing.longitude)
    if target is None:
        return None
    existing = session.scalar(
        select(ListingDistance).where(
            ListingDistance.listing_id == listing.id,
            ListingDistance.reference_key == reference.key,
            ListingDistance.reference_version == reference.version,
            ListingDistance.coordinate_hash == target.coordinate_hash,
            ListingDistance.provider == LOCAL_PROVIDER,
            ListingDistance.travel_mode == STRAIGHT_LINE_MODE,
        )
    )
    if existing is not None:
        return existing

    origin = Coordinates(reference.latitude, reference.longitude)
    distance = Decimal(str(haversine_distance_km(origin, target))).quantize(
        DISTANCE_PRECISION_KM, rounding=ROUND_HALF_UP
    )
    stored = ListingDistance(
        listing_id=listing.id,
        reference_key=reference.key,
        reference_version=reference.version,
        coordinate_hash=target.coordinate_hash,
        target_latitude=target.latitude,
        target_longitude=target.longitude,
        air_distance_km=distance,
        road_distance_km=None,
        drive_duration_minutes=None,
        provider=LOCAL_PROVIDER,
        travel_mode=STRAIGHT_LINE_MODE,
        calculated_at=calculated_at,
    )
    session.add(stored)
    return stored
