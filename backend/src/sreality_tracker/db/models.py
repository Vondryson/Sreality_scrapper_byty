"""SQLAlchemy models for the tracker state and immutable history."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sreality_tracker.db.base import Base
from sreality_tracker.domain.events import ListingEventType
from sreality_tracker.domain.listings import ListingKind


class ScrapeRunTrigger(StrEnum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class ScrapeRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class ImageArchiveStatus(StrEnum):
    SOURCE_ONLY = "source_only"
    PENDING = "pending"
    ARCHIVED = "archived"
    FAILED = "failed"


listing_kind_enum = SAEnum(
    ListingKind, name="listing_kind", values_callable=lambda e: [x.value for x in e]
)
run_trigger_enum = SAEnum(
    ScrapeRunTrigger,
    name="scrape_run_trigger",
    values_callable=lambda e: [x.value for x in e],
)
run_status_enum = SAEnum(
    ScrapeRunStatus,
    name="scrape_run_status",
    values_callable=lambda e: [x.value for x in e],
)
event_type_enum = SAEnum(
    ListingEventType,
    name="listing_event_type",
    values_callable=lambda e: [x.value for x in e],
)
image_status_enum = SAEnum(
    ImageArchiveStatus,
    name="image_archive_status",
    values_callable=lambda e: [x.value for x in e],
)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"
    __table_args__ = (
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="valid_times"),
        CheckConstraint("found_count >= 0", name="found_count_nonnegative"),
        CheckConstraint("new_count >= 0", name="new_count_nonnegative"),
        CheckConstraint("changed_count >= 0", name="changed_count_nonnegative"),
        CheckConstraint("error_count >= 0", name="error_count_nonnegative"),
        CheckConstraint("deactivated_count >= 0", name="deactivated_count_nonnegative"),
        CheckConstraint(
            "status <> 'succeeded' OR "
            "(finished_at IS NOT NULL AND chata_complete AND chalupa_complete)",
            name="succeeded_is_complete",
        ),
        Index("ix_scrape_runs_status_started_at", "status", text("started_at DESC")),
        Index("ix_scrape_runs_started_at", text("started_at DESC")),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    logical_key: Mapped[str] = mapped_column(String(160), unique=True)
    trigger: Mapped[ScrapeRunTrigger] = mapped_column(run_trigger_enum)
    status: Mapped[ScrapeRunStatus] = mapped_column(
        run_status_enum, default=ScrapeRunStatus.RUNNING
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    chata_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    chalupa_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    changed_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    deactivated_count: Mapped[int] = mapped_column(Integer, default=0)
    scraper_version: Mapped[str] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_summary: Mapped[str | None] = mapped_column(Text)

    observations: Mapped[list[ListingObservation]] = relationship(back_populates="run")
    events: Mapped[list[ListingEvent]] = relationship(back_populates="run")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint(
            "source_price_czk IS NULL OR source_price_czk >= 0", name="source_price_nonnegative"
        ),
        CheckConstraint("price_czk IS NULL OR price_czk >= 0", name="price_nonnegative"),
        CheckConstraint(
            "NOT price_on_request OR price_czk IS NULL", name="on_request_has_no_price"
        ),
        CheckConstraint(
            "source_price_czk IS DISTINCT FROM 0 OR (price_czk IS NULL AND price_on_request)",
            name="zero_price_is_on_request",
        ),
        CheckConstraint(
            "usable_area_m2 IS NULL OR usable_area_m2 >= 0", name="usable_area_nonnegative"
        ),
        CheckConstraint("land_area_m2 IS NULL OR land_area_m2 >= 0", name="land_area_nonnegative"),
        CheckConstraint(
            "building_area_m2 IS NULL OR building_area_m2 >= 0", name="building_area_nonnegative"
        ),
        CheckConstraint(
            "floor_area_m2 IS NULL OR floor_area_m2 >= 0", name="floor_area_nonnegative"
        ),
        CheckConstraint(
            "garden_area_m2 IS NULL OR garden_area_m2 >= 0", name="garden_area_nonnegative"
        ),
        CheckConstraint(
            "derived_price_per_sqm_czk IS NULL OR derived_price_per_sqm_czk >= 0",
            name="derived_price_per_sqm_nonnegative",
        ),
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)", name="coordinates_both_or_neither"
        ),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180", name="longitude_range"
        ),
        CheckConstraint(
            "(is_active AND inactive_at IS NULL) OR (NOT is_active AND inactive_at IS NOT NULL)",
            name="active_matches_inactive_at",
        ),
        CheckConstraint("first_seen_at <= last_seen_at", name="seen_times_ordered"),
        CheckConstraint(
            "detail_changed_at >= first_seen_at", name="detail_change_after_first_seen"
        ),
        Index(
            "ix_listings_active_kind_region_district",
            "kind",
            "region",
            "district",
            postgresql_where=text("is_active"),
        ),
        Index("ix_listings_active_price", "price_czk", postgresql_where=text("is_active")),
        Index(
            "ix_listings_active_usable_area", "usable_area_m2", postgresql_where=text("is_active")
        ),
        Index("ix_listings_active_land_area", "land_area_m2", postgresql_where=text("is_active")),
        Index(
            "ix_listings_active_derived_price_per_sqm",
            "derived_price_per_sqm_czk",
            postgresql_where=text("is_active"),
        ),
        Index("ix_listings_active_last_seen", "is_active", text("last_seen_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sreality_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    kind: Mapped[ListingKind] = mapped_column(listing_kind_enum)
    source_url: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    inactive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_price_czk: Mapped[int | None] = mapped_column(BigInteger)
    price_czk: Mapped[int | None] = mapped_column(BigInteger)
    price_on_request: Mapped[bool] = mapped_column(Boolean, default=False)
    currency_code: Mapped[str | None] = mapped_column(String(3))
    source_price_per_sqm_czk: Mapped[int | None] = mapped_column(BigInteger)
    derived_price_per_sqm_czk: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    price_note: Mapped[str | None] = mapped_column(Text)
    locality_text: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    region_source_id: Mapped[int | None] = mapped_column(BigInteger)
    district_source_id: Mapped[int | None] = mapped_column(BigInteger)
    municipality_source_id: Mapped[int | None] = mapped_column(BigInteger)
    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)
    location_inaccuracy: Mapped[str | None] = mapped_column(String(80))
    usable_area_m2: Mapped[int | None] = mapped_column(Integer)
    land_area_m2: Mapped[int | None] = mapped_column(Integer)
    building_area_m2: Mapped[int | None] = mapped_column(Integer)
    floor_area_m2: Mapped[int | None] = mapped_column(Integer)
    garden_area_m2: Mapped[int | None] = mapped_column(Integer)
    building_condition_code: Mapped[int | None] = mapped_column(Integer)
    building_type_code: Mapped[int | None] = mapped_column(Integer)
    object_type_code: Mapped[int | None] = mapped_column(Integer)
    room_count_code: Mapped[int | None] = mapped_column(Integer)
    energy_rating_code: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    detail_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    source_extra_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    observations: Mapped[list[ListingObservation]] = relationship(back_populates="listing")
    events: Mapped[list[ListingEvent]] = relationship(back_populates="listing")
    images: Mapped[list[ListingImage]] = relationship(back_populates="listing")
    distances: Mapped[list[ListingDistance]] = relationship(back_populates="listing")
    user_data: Mapped[UserListingData | None] = relationship(back_populates="listing")


class ListingObservation(Base):
    __tablename__ = "listing_observations"
    __table_args__ = (
        UniqueConstraint("listing_id", "run_id"),
        CheckConstraint(
            "source_price_czk IS NULL OR source_price_czk >= 0", name="source_price_nonnegative"
        ),
        CheckConstraint("price_czk IS NULL OR price_czk >= 0", name="price_nonnegative"),
        CheckConstraint(
            "NOT price_on_request OR price_czk IS NULL", name="on_request_has_no_price"
        ),
        CheckConstraint(
            "usable_area_m2 IS NULL OR usable_area_m2 >= 0", name="usable_area_nonnegative"
        ),
        CheckConstraint("land_area_m2 IS NULL OR land_area_m2 >= 0", name="land_area_nonnegative"),
        CheckConstraint(
            "building_area_m2 IS NULL OR building_area_m2 >= 0", name="building_area_nonnegative"
        ),
        CheckConstraint(
            "derived_price_per_sqm_czk IS NULL OR derived_price_per_sqm_czk >= 0",
            name="derived_price_per_sqm_nonnegative",
        ),
        Index(
            "ix_listing_observations_run_price",
            "run_id",
            "price_czk",
            postgresql_where=text("price_czk IS NOT NULL"),
        ),
        Index("ix_listing_observations_listing_observed", "listing_id", text("observed_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    run_id: Mapped[UUID] = mapped_column(ForeignKey("scrape_runs.id", ondelete="RESTRICT"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_price_czk: Mapped[int | None] = mapped_column(BigInteger)
    price_czk: Mapped[int | None] = mapped_column(BigInteger)
    price_on_request: Mapped[bool] = mapped_column(Boolean, default=False)
    usable_area_m2: Mapped[int | None] = mapped_column(Integer)
    land_area_m2: Mapped[int | None] = mapped_column(Integer)
    building_area_m2: Mapped[int | None] = mapped_column(Integer)
    derived_price_per_sqm_czk: Mapped[int | None] = mapped_column(BigInteger)
    detail_hash: Mapped[str] = mapped_column(String(64))
    raw_object_key: Mapped[str | None] = mapped_column(Text)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    listing: Mapped[Listing] = relationship(back_populates="observations")
    run: Mapped[ScrapeRun] = relationship(back_populates="observations")


class ListingEvent(Base):
    __tablename__ = "listing_events"
    __table_args__ = (
        UniqueConstraint("run_id", "listing_id", "event_type"),
        CheckConstraint(
            "old_price_czk IS NULL OR old_price_czk >= 0", name="old_price_nonnegative"
        ),
        CheckConstraint(
            "new_price_czk IS NULL OR new_price_czk >= 0", name="new_price_nonnegative"
        ),
        Index("ix_listing_events_listing_occurred", "listing_id", text("occurred_at DESC")),
        Index("ix_listing_events_type_occurred", "event_type", text("occurred_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    run_id: Mapped[UUID] = mapped_column(ForeignKey("scrape_runs.id", ondelete="RESTRICT"))
    event_type: Mapped[ListingEventType] = mapped_column(event_type_enum)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    old_price_czk: Mapped[int | None] = mapped_column(BigInteger)
    new_price_czk: Mapped[int | None] = mapped_column(BigInteger)
    changes_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    listing: Mapped[Listing] = relationship(back_populates="events")
    run: Mapped[ScrapeRun] = relationship(back_populates="events")


class ListingImage(Base):
    __tablename__ = "listing_images"
    __table_args__ = (
        UniqueConstraint("listing_id", "source_fingerprint"),
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint("width IS NULL OR width > 0", name="width_positive"),
        CheckConstraint("height IS NULL OR height > 0", name="height_positive"),
        CheckConstraint("first_seen_at <= last_seen_at", name="seen_times_ordered"),
        Index("ix_listing_images_listing_position", "listing_id", "position"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    source_image_id: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    source_fingerprint: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    archive_object_key: Mapped[str | None] = mapped_column(Text)
    archive_status: Mapped[ImageArchiveStatus] = mapped_column(
        image_status_enum, default=ImageArchiveStatus.SOURCE_ONLY
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))
    last_error: Mapped[str | None] = mapped_column(Text)

    listing: Mapped[Listing] = relationship(back_populates="images")


class ListingDistance(Base):
    __tablename__ = "listing_distances"
    __table_args__ = (
        UniqueConstraint(
            "listing_id",
            "reference_key",
            "reference_version",
            "coordinate_hash",
            "provider",
            "travel_mode",
        ),
        CheckConstraint("reference_version > 0", name="reference_version_positive"),
        CheckConstraint("target_latitude BETWEEN -90 AND 90", name="target_latitude_range"),
        CheckConstraint("target_longitude BETWEEN -180 AND 180", name="target_longitude_range"),
        CheckConstraint(
            "air_distance_km IS NULL OR air_distance_km >= 0", name="air_distance_nonnegative"
        ),
        CheckConstraint(
            "road_distance_km IS NULL OR road_distance_km >= 0", name="road_distance_nonnegative"
        ),
        CheckConstraint(
            "drive_duration_minutes IS NULL OR drive_duration_minutes >= 0",
            name="duration_nonnegative",
        ),
        Index(
            "ix_listing_distances_reference_road",
            "reference_key",
            "reference_version",
            "road_distance_km",
        ),
        Index("ix_listing_distances_listing_calculated", "listing_id", text("calculated_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    reference_key: Mapped[str] = mapped_column(String(80))
    reference_version: Mapped[int] = mapped_column(Integer)
    coordinate_hash: Mapped[str] = mapped_column(String(64))
    target_latitude: Mapped[float] = mapped_column(Double)
    target_longitude: Mapped[float] = mapped_column(Double)
    air_distance_km: Mapped[float | None] = mapped_column(Numeric(10, 3))
    road_distance_km: Mapped[float | None] = mapped_column(Numeric(10, 3))
    drive_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(40))
    travel_mode: Mapped[str] = mapped_column(String(32))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    listing: Mapped[Listing] = relationship(back_populates="distances")


class UserListingData(Base):
    __tablename__ = "user_listing_data"

    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="RESTRICT"), primary_key=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    private_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped[Listing] = relationship(back_populates="user_data")
