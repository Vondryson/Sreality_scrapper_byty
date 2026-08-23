"""Read models for listing detail, map data, history, and price medians."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.listing_contracts import ListingFilters, ListingStatusFilter
from sreality_tracker.api.listing_insight_contracts import (
    ListingDetailResponse,
    ListingEventItem,
    ListingHistoryResponse,
    ListingImageItem,
    MapListingItem,
    MapListingResponse,
    MedianPoint,
    PriceHistoryPoint,
    PriceMedianResponse,
)
from sreality_tracker.api.listing_repository import _conditions, _distance_value
from sreality_tracker.db.models import (
    Listing,
    ListingDistance,
    ListingEvent,
    ListingImage,
    ListingObservation,
    ScrapeRun,
    ScrapeRunStatus,
    UserListingData,
)
from sreality_tracker.distances.persistence import LOCAL_PROVIDER, STRAIGHT_LINE_MODE
from sreality_tracker.distances.road import DRIVING_MODE, GOOGLE_ROUTES_PROVIDER
from sreality_tracker.domain.events import ListingEventType


def get_listing_detail(session: Session, listing_id: int) -> ListingDetailResponse:
    air, road, duration = _distance_expressions()
    favorite = func.coalesce(UserListingData.is_favorite, False)
    row = session.execute(
        select(
            Listing,
            air.label("air_distance_km"),
            road.label("road_distance_km"),
            duration.label("drive_duration_minutes"),
            favorite.label("is_favorite"),
            UserListingData.private_note,
        )
        .outerjoin(UserListingData, UserListingData.listing_id == Listing.id)
        .where(Listing.id == listing_id)
    ).one_or_none()
    if row is None:
        raise ApiError(status_code=404, code="listing_not_found", message="Listing not found")
    listing, air_km, road_km, drive_minutes, is_favorite, private_note = row
    images = session.scalars(
        select(ListingImage)
        .where(ListingImage.listing_id == listing.id)
        .order_by(ListingImage.position, ListingImage.id)
    ).all()
    return ListingDetailResponse(
        id=listing.id,
        sreality_id=listing.sreality_id,
        kind=listing.kind,
        source_url=listing.source_url,
        name=listing.name,
        description=listing.description,
        price_czk=listing.price_czk,
        price_on_request=listing.price_on_request,
        price_note=listing.price_note,
        price_per_sqm_czk=listing.derived_price_per_sqm_czk,
        locality=listing.locality_text,
        region=listing.region,
        district=listing.district,
        municipality=listing.municipality,
        latitude=listing.latitude,
        longitude=listing.longitude,
        location_inaccuracy=listing.location_inaccuracy,
        usable_area_m2=listing.usable_area_m2,
        land_area_m2=listing.land_area_m2,
        building_area_m2=listing.building_area_m2,
        floor_area_m2=listing.floor_area_m2,
        garden_area_m2=listing.garden_area_m2,
        params=listing.params_json,
        air_distance_km=_optional_float(air_km),
        road_distance_km=_optional_float(road_km),
        drive_duration_minutes=drive_minutes,
        is_active=listing.is_active,
        first_seen_at=listing.first_seen_at,
        last_seen_at=listing.last_seen_at,
        inactive_at=listing.inactive_at,
        is_favorite=is_favorite,
        private_note=private_note,
        images=[
            ListingImageItem(
                source_url=image.source_url,
                position=image.position,
                width=image.width,
                height=image.height,
                archive_object_key=image.archive_object_key,
            )
            for image in images
        ],
    )


def get_listing_history(session: Session, listing_id: int) -> ListingHistoryResponse:
    _require_listing(session, listing_id)
    prices = session.execute(
        select(ListingObservation, ScrapeRun.status)
        .join(ScrapeRun, ScrapeRun.id == ListingObservation.run_id)
        .where(ListingObservation.listing_id == listing_id)
        .order_by(ListingObservation.observed_at, ListingObservation.id)
    ).all()
    events = session.scalars(
        select(ListingEvent)
        .where(ListingEvent.listing_id == listing_id)
        .order_by(ListingEvent.occurred_at, ListingEvent.id)
    ).all()
    return ListingHistoryResponse(
        listing_id=listing_id,
        prices=[
            PriceHistoryPoint(
                run_id=observation.run_id,
                run_status=status.value,
                observed_at=observation.observed_at,
                price_czk=observation.price_czk,
                price_on_request=observation.price_on_request,
                price_per_sqm_czk=observation.derived_price_per_sqm_czk,
            )
            for observation, status in prices
        ],
        events=[
            ListingEventItem(
                run_id=event.run_id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                old_price_czk=event.old_price_czk,
                new_price_czk=event.new_price_czk,
                changes=event.changes_json,
            )
            for event in events
        ],
    )


def list_map_listings(session: Session, filters: ListingFilters) -> MapListingResponse:
    air, road, duration = _distance_expressions()
    favorite = func.coalesce(UserListingData.is_favorite, False)
    conditions = _conditions(filters, air, road, duration, favorite)
    conditions.extend([Listing.latitude.is_not(None), Listing.longitude.is_not(None)])
    rows = session.execute(
        select(
            Listing,
            air.label("air_distance_km"),
            road.label("road_distance_km"),
            favorite.label("is_favorite"),
        )
        .outerjoin(UserListingData, UserListingData.listing_id == Listing.id)
        .where(*conditions)
        .order_by(Listing.sreality_id)
    ).all()
    items = [
        MapListingItem(
            id=listing.id,
            sreality_id=listing.sreality_id,
            kind=listing.kind,
            name=listing.name,
            locality=listing.locality_text,
            price_czk=listing.price_czk,
            latitude=listing.latitude,
            longitude=listing.longitude,
            air_distance_km=_optional_float(air_km),
            road_distance_km=_optional_float(road_km),
            is_favorite=is_favorite,
        )
        for listing, air_km, road_km, is_favorite in rows
        if listing.latitude is not None and listing.longitude is not None
    ]
    return MapListingResponse(items=items, total=len(items))


def get_price_medians(session: Session, filters: ListingFilters) -> PriceMedianResponse:
    air, road, duration = _distance_expressions()
    favorite = func.coalesce(UserListingData.is_favorite, False)
    current_conditions = _conditions(filters, air, road, duration, favorite)
    current_median, current_count = session.execute(
        select(
            func.percentile_cont(0.5).within_group(Listing.price_czk),
            func.count(Listing.price_czk),
        )
        .select_from(Listing)
        .outerjoin(UserListingData, UserListingData.listing_id == Listing.id)
        .where(Listing.price_czk.is_not(None), *current_conditions)
    ).one()

    history_conditions = _historical_conditions(filters, air, road, duration, favorite)
    history_rows = session.execute(
        select(
            ScrapeRun.id,
            ScrapeRun.started_at,
            func.percentile_cont(0.5).within_group(ListingObservation.price_czk),
            func.count(ListingObservation.price_czk),
        )
        .select_from(ScrapeRun)
        .join(ListingObservation, ListingObservation.run_id == ScrapeRun.id)
        .join(Listing, Listing.id == ListingObservation.listing_id)
        .outerjoin(UserListingData, UserListingData.listing_id == Listing.id)
        .where(
            ScrapeRun.status == ScrapeRunStatus.SUCCEEDED,
            ListingObservation.price_czk.is_not(None),
            *history_conditions,
        )
        .group_by(ScrapeRun.id, ScrapeRun.started_at)
        .order_by(ScrapeRun.started_at, ScrapeRun.id)
    ).all()
    return PriceMedianResponse(
        current_median_price_czk=_optional_float(current_median),
        current_sample_size=int(current_count),
        history=[
            MedianPoint(
                run_id=run_id,
                observed_at=observed_at,
                median_price_czk=float(median),
                sample_size=int(sample_size),
            )
            for run_id, observed_at, median, sample_size in history_rows
        ],
    )


def _historical_conditions(
    filters: ListingFilters,
    air: Any,
    road: Any,
    duration: Any,
    favorite: Any,
) -> list[Any]:
    conditions: list[Any] = []
    if filters.status is ListingStatusFilter.INACTIVE:
        conditions.append(False)
    elif filters.status not in (ListingStatusFilter.ACTIVE, ListingStatusFilter.ALL):
        event_type = {
            ListingStatusFilter.NEW: ListingEventType.CREATED,
            ListingStatusFilter.PRICE_DECREASED: ListingEventType.PRICE_DECREASED,
            ListingStatusFilter.REACTIVATED: ListingEventType.REACTIVATED,
        }[filters.status]
        conditions.append(
            select(ListingEvent.id)
            .where(
                ListingEvent.listing_id == Listing.id,
                ListingEvent.run_id == ScrapeRun.id,
                ListingEvent.event_type == event_type,
            )
            .exists()
        )
    if filters.kind is not None:
        conditions.append(Listing.kind == filters.kind)
    if filters.region is not None:
        conditions.append(Listing.region == filters.region)
    if filters.district is not None:
        conditions.append(Listing.district == filters.district)
    _append_observation_range(
        conditions, ListingObservation.price_czk, filters.price_min, filters.price_max
    )
    _append_observation_range(
        conditions,
        ListingObservation.usable_area_m2,
        filters.usable_area_min,
        filters.usable_area_max,
    )
    _append_observation_range(
        conditions,
        ListingObservation.land_area_m2,
        filters.land_area_min,
        filters.land_area_max,
    )
    _append_observation_range(
        conditions,
        ListingObservation.derived_price_per_sqm_czk,
        filters.price_per_sqm_min,
        filters.price_per_sqm_max,
    )
    if filters.air_distance_max_km is not None:
        conditions.append(air <= filters.air_distance_max_km)
    if filters.road_distance_max_km is not None:
        conditions.append(road <= filters.road_distance_max_km)
    if filters.drive_duration_max_minutes is not None:
        conditions.append(duration <= filters.drive_duration_max_minutes)
    if filters.favorite is not None:
        conditions.append(favorite.is_(filters.favorite))
    return conditions


def _append_observation_range(
    conditions: list[Any], column: Any, minimum: int | None, maximum: int | None
) -> None:
    if minimum is not None:
        conditions.append(column >= minimum)
    if maximum is not None:
        conditions.append(column <= maximum)


def _distance_expressions() -> tuple[Any, Any, Any]:
    return (
        _distance_value(ListingDistance.air_distance_km, LOCAL_PROVIDER, STRAIGHT_LINE_MODE),
        _distance_value(ListingDistance.road_distance_km, GOOGLE_ROUTES_PROVIDER, DRIVING_MODE),
        _distance_value(
            ListingDistance.drive_duration_minutes, GOOGLE_ROUTES_PROVIDER, DRIVING_MODE
        ),
    )


def _require_listing(session: Session, listing_id: int) -> None:
    if session.scalar(select(Listing.id).where(Listing.id == listing_id)) is None:
        raise ApiError(status_code=404, code="listing_not_found", message="Listing not found")


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
