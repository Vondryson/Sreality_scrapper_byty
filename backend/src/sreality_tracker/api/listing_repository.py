"""SQLAlchemy query builder for filtered listing collection responses."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from sreality_tracker.api.listing_contracts import (
    ListingFilters,
    ListingListItem,
    ListingPage,
    ListingSort,
    ListingStatusFilter,
)
from sreality_tracker.db.models import (
    Listing,
    ListingDistance,
    ListingEvent,
    ScrapeRun,
    ScrapeRunStatus,
    UserListingData,
)
from sreality_tracker.distances.persistence import LOCAL_PROVIDER, STRAIGHT_LINE_MODE
from sreality_tracker.distances.road import DRIVING_MODE, GOOGLE_ROUTES_PROVIDER
from sreality_tracker.domain.events import ListingEventType
from sreality_tracker.domain.reference_points import PRAGUE_CENTER_V1


def list_listings(session: Session, filters: ListingFilters) -> ListingPage:
    air_distance = _distance_value(
        ListingDistance.air_distance_km, LOCAL_PROVIDER, STRAIGHT_LINE_MODE
    )
    road_distance = _distance_value(
        ListingDistance.road_distance_km, GOOGLE_ROUTES_PROVIDER, DRIVING_MODE
    )
    drive_duration = _distance_value(
        ListingDistance.drive_duration_minutes, GOOGLE_ROUTES_PROVIDER, DRIVING_MODE
    )
    favorite = func.coalesce(UserListingData.is_favorite, False)
    conditions = _conditions(filters, air_distance, road_distance, drive_duration, favorite)

    total = session.scalar(
        select(func.count())
        .select_from(Listing)
        .outerjoin(UserListingData, UserListingData.listing_id == Listing.id)
        .where(*conditions)
    )
    total_count = int(total or 0)
    statement = (
        select(
            Listing,
            air_distance.label("air_distance_km"),
            road_distance.label("road_distance_km"),
            drive_duration.label("drive_duration_minutes"),
            favorite.label("is_favorite"),
        )
        .outerjoin(UserListingData, UserListingData.listing_id == Listing.id)
        .where(*conditions)
        .order_by(*_order_by(filters.sort, air_distance, road_distance, drive_duration))
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    items = [_to_item(*row) for row in session.execute(statement).all()]
    pages = (total_count + filters.page_size - 1) // filters.page_size
    return ListingPage(
        items=items,
        page=filters.page,
        page_size=filters.page_size,
        total=total_count,
        pages=pages,
    )


def _distance_value(column: Any, provider: str, travel_mode: str) -> Any:
    return (
        select(column)
        .where(
            ListingDistance.listing_id == Listing.id,
            ListingDistance.reference_key == PRAGUE_CENTER_V1.key,
            ListingDistance.reference_version == PRAGUE_CENTER_V1.version,
            ListingDistance.provider == provider,
            ListingDistance.travel_mode == travel_mode,
        )
        .order_by(ListingDistance.calculated_at.desc())
        .limit(1)
        .correlate(Listing)
        .scalar_subquery()
    )


def _conditions(
    filters: ListingFilters,
    air_distance: Any,
    road_distance: Any,
    drive_duration: Any,
    favorite: Any,
) -> list[Any]:
    conditions: list[Any] = []
    if filters.status is ListingStatusFilter.ACTIVE:
        conditions.append(Listing.is_active.is_(True))
    elif filters.status is ListingStatusFilter.INACTIVE:
        conditions.append(Listing.is_active.is_(False))
    elif filters.status is not ListingStatusFilter.ALL:
        event_type = {
            ListingStatusFilter.NEW: ListingEventType.CREATED,
            ListingStatusFilter.PRICE_DECREASED: ListingEventType.PRICE_DECREASED,
            ListingStatusFilter.REACTIVATED: ListingEventType.REACTIVATED,
        }[filters.status]
        latest_run = (
            select(ScrapeRun.id)
            .where(ScrapeRun.status == ScrapeRunStatus.SUCCEEDED)
            .order_by(ScrapeRun.started_at.desc(), ScrapeRun.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        conditions.extend(
            [
                Listing.is_active.is_(True),
                exists(
                    select(ListingEvent.id).where(
                        ListingEvent.listing_id == Listing.id,
                        ListingEvent.run_id == latest_run,
                        ListingEvent.event_type == event_type,
                    )
                ),
            ]
        )
    if filters.kind is not None:
        conditions.append(Listing.kind == filters.kind)
    if filters.region is not None:
        conditions.append(Listing.region == filters.region)
    if filters.district is not None:
        conditions.append(Listing.district == filters.district)
    _append_range(conditions, Listing.price_czk, filters.price_min, filters.price_max)
    _append_range(
        conditions, Listing.usable_area_m2, filters.usable_area_min, filters.usable_area_max
    )
    _append_range(conditions, Listing.land_area_m2, filters.land_area_min, filters.land_area_max)
    _append_range(
        conditions,
        Listing.derived_price_per_sqm_czk,
        filters.price_per_sqm_min,
        filters.price_per_sqm_max,
    )
    if filters.air_distance_max_km is not None:
        conditions.append(air_distance <= filters.air_distance_max_km)
    if filters.road_distance_max_km is not None:
        conditions.append(road_distance <= filters.road_distance_max_km)
    if filters.drive_duration_max_minutes is not None:
        conditions.append(drive_duration <= filters.drive_duration_max_minutes)
    if filters.favorite is not None:
        conditions.append(favorite.is_(filters.favorite))
    return conditions


def _append_range(
    conditions: list[Any], column: Any, minimum: int | None, maximum: int | None
) -> None:
    if minimum is not None:
        conditions.append(column >= minimum)
    if maximum is not None:
        conditions.append(column <= maximum)


def _order_by(sort: ListingSort, air: Any, road: Any, duration: Any) -> Sequence[Any]:
    primary = {
        ListingSort.NEWEST: Listing.first_seen_at.desc(),
        ListingSort.PRICE_ASC: Listing.price_czk.asc().nulls_last(),
        ListingSort.PRICE_DESC: Listing.price_czk.desc().nulls_last(),
        ListingSort.USABLE_AREA_DESC: Listing.usable_area_m2.desc().nulls_last(),
        ListingSort.LAND_AREA_DESC: Listing.land_area_m2.desc().nulls_last(),
        ListingSort.PRICE_PER_SQM_ASC: Listing.derived_price_per_sqm_czk.asc().nulls_last(),
        ListingSort.AIR_DISTANCE_ASC: air.asc().nulls_last(),
        ListingSort.ROAD_DISTANCE_ASC: road.asc().nulls_last(),
        ListingSort.DRIVE_DURATION_ASC: duration.asc().nulls_last(),
    }[sort]
    return primary, Listing.sreality_id.asc()


def _to_item(
    listing: Listing,
    air_distance_km: Any,
    road_distance_km: Any,
    drive_duration_minutes: Any,
    is_favorite: bool,
) -> ListingListItem:
    return ListingListItem(
        id=listing.id,
        sreality_id=listing.sreality_id,
        kind=listing.kind,
        name=listing.name,
        locality=listing.locality_text,
        region=listing.region,
        district=listing.district,
        municipality=listing.municipality,
        price_czk=listing.price_czk,
        usable_area_m2=listing.usable_area_m2,
        land_area_m2=listing.land_area_m2,
        price_per_sqm_czk=listing.derived_price_per_sqm_czk,
        latitude=listing.latitude,
        longitude=listing.longitude,
        air_distance_km=None if air_distance_km is None else float(air_distance_km),
        road_distance_km=None if road_distance_km is None else float(road_distance_km),
        drive_duration_minutes=drive_duration_minutes,
        is_active=listing.is_active,
        is_favorite=is_favorite,
    )
