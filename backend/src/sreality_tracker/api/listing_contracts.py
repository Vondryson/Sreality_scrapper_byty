"""Query and response contracts for listing collection endpoints."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from sreality_tracker.api.contracts import ApiModel
from sreality_tracker.domain.listings import ListingKind


class ListingStatusFilter(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ALL = "all"
    NEW = "new"
    PRICE_DECREASED = "price_decreased"
    REACTIVATED = "reactivated"


class ListingSort(StrEnum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    USABLE_AREA_DESC = "usable_area_desc"
    LAND_AREA_DESC = "land_area_desc"
    PRICE_PER_SQM_ASC = "price_per_sqm_asc"
    AIR_DISTANCE_ASC = "air_distance_asc"
    ROAD_DISTANCE_ASC = "road_distance_asc"
    DRIVE_DURATION_ASC = "drive_duration_asc"


class ListingFilters(ApiModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    status: ListingStatusFilter = ListingStatusFilter.ACTIVE
    kind: ListingKind | None = None
    region: str | None = Field(default=None, min_length=1, max_length=120)
    district: str | None = Field(default=None, min_length=1, max_length=120)
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    usable_area_min: int | None = Field(default=None, ge=0)
    usable_area_max: int | None = Field(default=None, ge=0)
    land_area_min: int | None = Field(default=None, ge=0)
    land_area_max: int | None = Field(default=None, ge=0)
    price_per_sqm_min: int | None = Field(default=None, ge=0)
    price_per_sqm_max: int | None = Field(default=None, ge=0)
    air_distance_max_km: float | None = Field(default=None, ge=0)
    road_distance_max_km: float | None = Field(default=None, ge=0)
    drive_duration_max_minutes: int | None = Field(default=None, ge=0)
    favorite: bool | None = None
    sort: ListingSort = ListingSort.NEWEST

    @model_validator(mode="after")
    def validate_ranges(self) -> ListingFilters:
        for minimum_name, maximum_name in (
            ("price_min", "price_max"),
            ("usable_area_min", "usable_area_max"),
            ("land_area_min", "land_area_max"),
            ("price_per_sqm_min", "price_per_sqm_max"),
        ):
            minimum = getattr(self, minimum_name)
            maximum = getattr(self, maximum_name)
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"{minimum_name} must not exceed {maximum_name}")
        return self


class ListingListItem(ApiModel):
    id: int
    sreality_id: int
    kind: ListingKind
    name: str | None
    locality: str | None
    region: str | None
    district: str | None
    municipality: str | None
    price_czk: int | None
    usable_area_m2: int | None
    land_area_m2: int | None
    price_per_sqm_czk: int | None
    latitude: float | None
    longitude: float | None
    air_distance_km: float | None
    road_distance_km: float | None
    drive_duration_minutes: int | None
    is_active: bool
    is_favorite: bool


class ListingPage(ApiModel):
    items: list[ListingListItem]
    page: int
    page_size: int
    total: int
    pages: int
