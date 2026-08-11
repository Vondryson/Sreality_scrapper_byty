"""Cached Google Routes persistence and retryable listing backfill."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sreality_tracker.db.models import Listing, ListingDistance
from sreality_tracker.distances.air import Coordinates, optional_coordinates
from sreality_tracker.distances.persistence import DISTANCE_PRECISION_KM
from sreality_tracker.distances.routes import RoutesClient, RoutesError
from sreality_tracker.domain.reference_points import PRAGUE_CENTER_V1, ReferencePoint

GOOGLE_ROUTES_PROVIDER = "google_routes"
DRIVING_MODE = "driving"


@dataclass(frozen=True, slots=True)
class RoadDistanceResult:
    distance: ListingDistance | None
    cache_hit: bool
    failed: bool


@dataclass(frozen=True, slots=True)
class BackfillResult:
    considered: int
    created: int
    cache_hits: int
    failed: int
    provider_requests: int


class RoadDistanceEnricher:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        client: RoutesClient,
        reference: ReferencePoint = PRAGUE_CENTER_V1,
    ) -> None:
        self._session_factory = session_factory
        self._client = client
        self._reference = reference

    def enrich(self, listing_id: int) -> RoadDistanceResult:
        with self._session_factory.begin() as session:
            listing = session.get(Listing, listing_id)
            if listing is None:
                return RoadDistanceResult(distance=None, cache_hit=False, failed=True)
            return ensure_road_distance(
                session,
                listing=listing,
                client=self._client,
                reference=self._reference,
            )

    def backfill(self, *, limit: int = 300) -> BackfillResult:
        if not 1 <= limit <= 300:
            raise ValueError("backfill limit must be between 1 and 300")
        with self._session_factory() as session:
            listing_ids = list(
                session.scalars(
                    select(Listing.id)
                    .where(Listing.latitude.is_not(None), Listing.longitude.is_not(None))
                    .order_by(Listing.id)
                )
            )
        before = self._client.request_count
        created = cache_hits = failed = 0
        considered = 0
        for listing_id in listing_ids:
            if self._client.request_count - before >= limit:
                break
            considered += 1
            result = self.enrich(listing_id)
            if result.failed:
                failed += 1
            elif result.cache_hit:
                cache_hits += 1
            elif result.distance is not None:
                created += 1
        return BackfillResult(
            considered=considered,
            created=created,
            cache_hits=cache_hits,
            failed=failed,
            provider_requests=self._client.request_count - before,
        )


def ensure_road_distance(
    session: Session,
    *,
    listing: Listing,
    client: RoutesClient,
    calculated_at: datetime | None = None,
    reference: ReferencePoint = PRAGUE_CENTER_V1,
) -> RoadDistanceResult:
    target = optional_coordinates(listing.latitude, listing.longitude)
    if target is None:
        return RoadDistanceResult(distance=None, cache_hit=False, failed=False)
    existing = session.scalar(
        select(ListingDistance).where(
            ListingDistance.listing_id == listing.id,
            ListingDistance.reference_key == reference.key,
            ListingDistance.reference_version == reference.version,
            ListingDistance.coordinate_hash == target.coordinate_hash,
            ListingDistance.provider == GOOGLE_ROUTES_PROVIDER,
            ListingDistance.travel_mode == DRIVING_MODE,
        )
    )
    if existing is not None:
        return RoadDistanceResult(distance=existing, cache_hit=True, failed=False)
    try:
        route = client.compute_route(
            origin=Coordinates(reference.latitude, reference.longitude),
            destination=target,
        )
    except RoutesError:
        return RoadDistanceResult(distance=None, cache_hit=False, failed=True)

    road_km = (Decimal(route.distance_meters) / Decimal(1000)).quantize(
        DISTANCE_PRECISION_KM, rounding=ROUND_HALF_UP
    )
    duration_minutes = int(
        (route.duration_seconds / Decimal(60)).quantize(Decimal("1"), rounding=ROUND_CEILING)
    )
    stored = ListingDistance(
        listing_id=listing.id,
        reference_key=reference.key,
        reference_version=reference.version,
        coordinate_hash=target.coordinate_hash,
        target_latitude=target.latitude,
        target_longitude=target.longitude,
        air_distance_km=None,
        road_distance_km=road_km,
        drive_duration_minutes=duration_minutes,
        provider=GOOGLE_ROUTES_PROVIDER,
        travel_mode=DRIVING_MODE,
        calculated_at=calculated_at or datetime.now(UTC),
    )
    session.add(stored)
    return RoadDistanceResult(distance=stored, cache_hit=False, failed=False)
