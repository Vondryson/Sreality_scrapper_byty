"""Contracts for listing detail, history, map, and price analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sreality_tracker.api.contracts import ApiModel
from sreality_tracker.domain.events import ListingEventType
from sreality_tracker.domain.listings import ListingKind


class ListingImageItem(ApiModel):
    source_url: str
    position: int
    width: int | None
    height: int | None
    archive_object_key: str | None


class ListingDetailResponse(ApiModel):
    id: int
    sreality_id: int
    kind: ListingKind
    source_url: str
    name: str | None
    description: str | None
    price_czk: int | None
    price_on_request: bool
    price_note: str | None
    price_per_sqm_czk: int | None
    locality: str | None
    region: str | None
    district: str | None
    municipality: str | None
    latitude: float | None
    longitude: float | None
    location_inaccuracy: str | None
    usable_area_m2: int | None
    land_area_m2: int | None
    building_area_m2: int | None
    floor_area_m2: int | None
    garden_area_m2: int | None
    params: dict[str, Any]
    air_distance_km: float | None
    road_distance_km: float | None
    drive_duration_minutes: int | None
    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime
    inactive_at: datetime | None
    is_favorite: bool
    private_note: str | None
    images: list[ListingImageItem]


class PriceHistoryPoint(ApiModel):
    run_id: UUID
    run_status: str
    observed_at: datetime
    price_czk: int | None
    price_on_request: bool
    price_per_sqm_czk: int | None


class ListingEventItem(ApiModel):
    run_id: UUID
    event_type: ListingEventType
    occurred_at: datetime
    old_price_czk: int | None
    new_price_czk: int | None
    changes: dict[str, Any]


class ListingHistoryResponse(ApiModel):
    listing_id: int
    prices: list[PriceHistoryPoint]
    events: list[ListingEventItem]


class MapListingItem(ApiModel):
    id: int
    sreality_id: int
    kind: ListingKind
    name: str | None
    locality: str | None
    price_czk: int | None
    latitude: float
    longitude: float
    air_distance_km: float | None
    road_distance_km: float | None
    is_favorite: bool


class MapListingResponse(ApiModel):
    items: list[MapListingItem]
    total: int


class MedianPoint(ApiModel):
    run_id: UUID
    observed_at: datetime
    median_price_czk: float
    sample_size: int


class PriceMedianResponse(ApiModel):
    current_median_price_czk: float | None
    current_sample_size: int
    history: list[MedianPoint]
