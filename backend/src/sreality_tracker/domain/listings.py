"""Framework-independent domain models for parsed Sreality listings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ListingKind(StrEnum):
    CHATA = "chata"
    CHALUPA = "chalupa"

    @property
    def search_slug(self) -> str:
        return "chaty" if self is ListingKind.CHATA else "chalupy"

    @property
    def subtype(self) -> int:
        return 33 if self is ListingKind.CHATA else 43

    @classmethod
    def from_subtype(cls, subtype: int) -> ListingKind:
        if subtype == 33:
            return cls.CHATA
        if subtype == 43:
            return cls.CHALUPA
        raise ValueError(f"unsupported listing subtype: {subtype}")


@dataclass(frozen=True, slots=True)
class Price:
    source_price_czk: int | None
    price_czk: int | None
    price_on_request: bool
    source_price_per_sqm_czk: int | None
    derived_price_per_sqm_czk: int | None


@dataclass(frozen=True, slots=True)
class Locality:
    display_text: str | None
    country: str | None
    region: str | None
    district: str | None
    municipality: str | None
    region_source_id: int | None
    district_source_id: int | None
    municipality_source_id: int | None
    latitude: float | None
    longitude: float | None
    inaccuracy_type: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    source_id: str | None
    source_url: str | None
    position: int | None
    width: int | None
    height: int | None
    alt: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SearchListing:
    sreality_id: int
    kind: ListingKind
    name: str | None
    locality: Locality
    price: Price
    images: tuple[ImageMetadata, ...]
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class SearchPage:
    kind: ListingKind
    page: int
    limit: int
    total: int
    listings: tuple[SearchListing, ...]
    warnings: tuple[object, ...]
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ListingDetail:
    sreality_id: int
    kind: ListingKind
    source_url: str
    name: str | None
    description: str | None
    price_note: str | None
    price: Price
    locality: Locality
    usable_area_m2: int | None
    land_area_m2: int | None
    building_area_m2: int | None
    floor_area_m2: int | None
    garden_area_m2: int | None
    building_condition_code: int | None
    building_type_code: int | None
    object_type_code: int | None
    room_count_code: int | None
    energy_rating_code: int | None
    images: tuple[ImageMetadata, ...]
    params: dict[str, Any]
    raw: dict[str, Any]
