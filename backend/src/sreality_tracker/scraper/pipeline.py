"""Transactional scraper run and listing-observation persistence."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from sreality_tracker.db.models import (
    ImageArchiveStatus,
    Listing,
    ListingEvent,
    ListingImage,
    ListingObservation,
    ScrapeRun,
    ScrapeRunStatus,
    ScrapeRunTrigger,
)
from sreality_tracker.distances.persistence import ensure_air_distance
from sreality_tracker.distances.road import RoadDistanceEnricher
from sreality_tracker.domain.events import (
    EventDraft,
    ListingEventType,
    ListingState,
    deactivation_event,
    observation_events,
)
from sreality_tracker.domain.listings import ImageMetadata, ListingDetail, ListingKind
from sreality_tracker.scraper.source import ListingSource
from sreality_tracker.storage.raw import RawStorage, serialize_payload


class PipelineError(RuntimeError):
    """Raised when persisted identity conflicts with the fetched source data."""


class DeactivationSafetyError(PipelineError):
    """Raised when bulk deactivation is attempted without a complete successful run."""


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: UUID
    logical_key: str
    status: ScrapeRunStatus
    found_count: int
    new_count: int
    changed_count: int
    error_count: int
    deactivated_count: int
    chata_complete: bool
    chalupa_complete: bool


class ScrapePipeline:
    """Coordinate both categories and persist every listing in its own transaction."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        source: ListingSource,
        raw_storage: RawStorage,
        scraper_version: str,
        road_distance_enricher: RoadDistanceEnricher | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if not scraper_version.strip():
            raise ValueError("scraper_version must not be empty")
        self._session_factory = session_factory
        self._source = source
        self._raw_storage = raw_storage
        self._scraper_version = scraper_version
        self._road_distance_enricher = road_distance_enricher
        self._clock = clock

    def execute(
        self, *, logical_key: str, trigger: ScrapeRunTrigger = ScrapeRunTrigger.MANUAL
    ) -> RunResult:
        normalized_key = logical_key.strip()
        if not normalized_key or len(normalized_key) > 160:
            raise ValueError("logical_key must contain 1 to 160 characters")

        existing = self._find_run(normalized_key)
        if existing is not None and existing.status is not ScrapeRunStatus.RUNNING:
            return _run_result(existing)
        run = existing or self._create_run(normalized_key, trigger)

        errors: list[tuple[ListingKind, Exception]] = []
        completed: set[ListingKind] = set()
        for kind in ListingKind:
            try:
                for fetched in self._source.iter_kind(kind):
                    listing_id = self._persist_detail(run.id, fetched.detail)
                    if listing_id is not None and self._road_distance_enricher is not None:
                        self._road_distance_enricher.enrich(listing_id)
                completed.add(kind)
            except Exception as error:
                errors.append((kind, error))

        return self._finish_run(run.id, completed=completed, errors=errors)

    def _find_run(self, logical_key: str) -> ScrapeRun | None:
        with self._session_factory() as session:
            return session.scalar(select(ScrapeRun).where(ScrapeRun.logical_key == logical_key))

    def _create_run(self, logical_key: str, trigger: ScrapeRunTrigger) -> ScrapeRun:
        started_at = _aware(self._clock())
        with self._session_factory.begin() as session:
            run = ScrapeRun(
                logical_key=logical_key,
                trigger=trigger,
                status=ScrapeRunStatus.RUNNING,
                started_at=started_at,
                scraper_version=self._scraper_version,
            )
            session.add(run)
            session.flush()
            run_id = run.id
        with self._session_factory() as session:
            return session.get_one(ScrapeRun, run_id)

    def _persist_detail(self, run_id: UUID, detail: ListingDetail) -> int | None:
        observed_at = _aware(self._clock())
        snapshot = _snapshot(detail)
        detail_hash = serialize_payload(_detail_content(detail)).sha256

        with self._session_factory.begin() as session:
            run = session.get_one(ScrapeRun, run_id)
            listing = session.scalar(
                select(Listing).where(Listing.sreality_id == detail.sreality_id).with_for_update()
            )
            if listing is not None:
                existing_observation = session.scalar(
                    select(ListingObservation.id).where(
                        ListingObservation.listing_id == listing.id,
                        ListingObservation.run_id == run.id,
                    )
                )
                if existing_observation is not None:
                    return listing.id

            previous_state = (
                None
                if listing is None
                else ListingState(
                    price_czk=listing.price_czk,
                    detail_hash=listing.content_hash,
                    is_active=listing.is_active,
                )
            )

            raw_ref = self._raw_storage.store_json(
                run_id=run.id, sreality_id=detail.sreality_id, payload=detail.raw
            )
            if listing is None:
                listing = Listing(
                    sreality_id=detail.sreality_id,
                    kind=detail.kind,
                    source_url=detail.source_url,
                    is_active=True,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    inactive_at=None,
                    content_hash=detail_hash,
                    detail_changed_at=observed_at,
                )
                session.add(listing)
                session.flush()
            else:
                if listing.kind is not detail.kind:
                    raise PipelineError(f"listing {detail.sreality_id} changed immutable category")
                if listing.content_hash != detail_hash:
                    listing.detail_changed_at = observed_at
                listing.last_seen_at = observed_at
                listing.is_active = True
                listing.inactive_at = None

            _apply_current_state(listing, detail, detail_hash, observed_at)
            ensure_air_distance(session, listing=listing, calculated_at=observed_at)
            _upsert_images(session, listing, detail.images, observed_at)
            current_state = ListingState(
                price_czk=detail.price.price_czk,
                detail_hash=detail_hash,
                is_active=True,
            )
            for draft in observation_events(previous_state, current_state):
                _add_event(session, listing, run, draft, observed_at)
            session.add(
                ListingObservation(
                    listing_id=listing.id,
                    run_id=run.id,
                    observed_at=observed_at,
                    source_price_czk=detail.price.source_price_czk,
                    price_czk=detail.price.price_czk,
                    price_on_request=detail.price.price_on_request,
                    usable_area_m2=detail.usable_area_m2,
                    land_area_m2=detail.land_area_m2,
                    building_area_m2=detail.building_area_m2,
                    derived_price_per_sqm_czk=detail.price.derived_price_per_sqm_czk,
                    detail_hash=detail_hash,
                    raw_object_key=raw_ref.key,
                    snapshot_json=snapshot,
                )
            )
            return listing.id

    def _finish_run(
        self,
        run_id: UUID,
        *,
        completed: set[ListingKind],
        errors: list[tuple[ListingKind, Exception]],
    ) -> RunResult:
        with self._session_factory.begin() as session:
            run = session.get_one(ScrapeRun, run_id)
            observations = list(
                session.execute(
                    select(ListingObservation, Listing)
                    .join(Listing, Listing.id == ListingObservation.listing_id)
                    .where(ListingObservation.run_id == run.id)
                )
            )
            run.found_count = len(observations)
            events = list(
                session.scalars(select(ListingEvent).where(ListingEvent.run_id == run.id))
            )
            run.new_count = sum(event.event_type is ListingEventType.CREATED for event in events)
            run.changed_count = len(
                {
                    event.listing_id
                    for event in events
                    if event.event_type
                    in {
                        ListingEventType.PRICE_DECREASED,
                        ListingEventType.PRICE_INCREASED,
                        ListingEventType.DETAILS_CHANGED,
                        ListingEventType.REACTIVATED,
                    }
                }
            )
            run.error_count = len(errors)
            run.chata_complete = ListingKind.CHATA in completed
            run.chalupa_complete = ListingKind.CHALUPA in completed
            run.finished_at = _aware(self._clock())
            if not errors:
                run.status = ScrapeRunStatus.SUCCEEDED
            elif run.found_count or completed:
                run.status = ScrapeRunStatus.PARTIAL
            else:
                run.status = ScrapeRunStatus.FAILED
            if errors:
                kinds = ",".join(kind.value for kind, _error in errors)
                types = ",".join(type(error).__name__ for _kind, error in errors)
                run.error_code = f"category_failed:{kinds}"
                run.error_summary = f"error_types:{types}"
            if run.status is ScrapeRunStatus.SUCCEEDED:
                run.deactivated_count = deactivate_missing_listings(
                    session, run=run, occurred_at=run.finished_at
                )
            session.flush()
            result = _run_result(run)
        return result


def _apply_current_state(
    listing: Listing, detail: ListingDetail, detail_hash: str, observed_at: datetime
) -> None:
    locality = detail.locality
    price = detail.price
    listing.source_url = detail.source_url
    listing.source_price_czk = price.source_price_czk
    listing.price_czk = price.price_czk
    listing.price_on_request = price.price_on_request
    listing.currency_code = "CZK"
    listing.source_price_per_sqm_czk = price.source_price_per_sqm_czk
    listing.derived_price_per_sqm_czk = price.derived_price_per_sqm_czk
    listing.name = detail.name
    listing.description = detail.description
    listing.price_note = detail.price_note
    listing.locality_text = locality.display_text
    listing.country = locality.country
    listing.region = locality.region
    listing.district = locality.district
    listing.municipality = locality.municipality
    listing.region_source_id = locality.region_source_id
    listing.district_source_id = locality.district_source_id
    listing.municipality_source_id = locality.municipality_source_id
    listing.latitude = locality.latitude
    listing.longitude = locality.longitude
    listing.location_inaccuracy = locality.inaccuracy_type
    listing.usable_area_m2 = detail.usable_area_m2
    listing.land_area_m2 = detail.land_area_m2
    listing.building_area_m2 = detail.building_area_m2
    listing.floor_area_m2 = detail.floor_area_m2
    listing.garden_area_m2 = detail.garden_area_m2
    listing.building_condition_code = detail.building_condition_code
    listing.building_type_code = detail.building_type_code
    listing.object_type_code = detail.object_type_code
    listing.room_count_code = detail.room_count_code
    listing.energy_rating_code = detail.energy_rating_code
    listing.content_hash = detail_hash
    listing.params_json = detail.params
    listing.source_extra_json = detail.raw
    listing.updated_at = observed_at


def _upsert_images(
    session: Session,
    listing: Listing,
    images: tuple[ImageMetadata, ...],
    observed_at: datetime,
) -> None:
    for fallback_position, image in enumerate(images):
        if image.source_url is None:
            continue
        identity = f"id:{image.source_id}" if image.source_id else f"url:{image.source_url}"
        fingerprint = hashlib.sha256(identity.encode()).hexdigest()
        stored = session.scalar(
            select(ListingImage).where(
                ListingImage.listing_id == listing.id,
                ListingImage.source_fingerprint == fingerprint,
            )
        )
        position = (
            image.position
            if image.position is not None and image.position >= 0
            else fallback_position
        )
        if stored is None:
            session.add(
                ListingImage(
                    listing_id=listing.id,
                    source_image_id=image.source_id,
                    source_url=image.source_url,
                    source_fingerprint=fingerprint,
                    position=position,
                    width=image.width,
                    height=image.height,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    archive_status=ImageArchiveStatus.SOURCE_ONLY,
                )
            )
        else:
            stored.source_url = image.source_url
            stored.position = position
            stored.width = image.width
            stored.height = image.height
            stored.last_seen_at = observed_at


def _snapshot(detail: ListingDetail) -> dict[str, object]:
    return {
        "sreality_id": detail.sreality_id,
        "kind": detail.kind.value,
        "source_url": detail.source_url,
        "name": detail.name,
        "description": detail.description,
        "price_note": detail.price_note,
        "price": {
            "source_price_czk": detail.price.source_price_czk,
            "price_czk": detail.price.price_czk,
            "price_on_request": detail.price.price_on_request,
            "source_price_per_sqm_czk": detail.price.source_price_per_sqm_czk,
            "derived_price_per_sqm_czk": detail.price.derived_price_per_sqm_czk,
        },
        "locality": detail.locality.raw,
        "usable_area_m2": detail.usable_area_m2,
        "land_area_m2": detail.land_area_m2,
        "building_area_m2": detail.building_area_m2,
        "floor_area_m2": detail.floor_area_m2,
        "garden_area_m2": detail.garden_area_m2,
        "building_condition_code": detail.building_condition_code,
        "building_type_code": detail.building_type_code,
        "object_type_code": detail.object_type_code,
        "room_count_code": detail.room_count_code,
        "energy_rating_code": detail.energy_rating_code,
        "params": detail.params,
        "source": detail.raw,
    }


def _detail_content(detail: ListingDetail) -> dict[str, object]:
    price_source_keys = {
        "price",
        "priceCzk",
        "priceCzkPerSqM",
        "priceSummaryCzk",
        "priceSummaryOldCzk",
        "priceSummaryUnitCb",
        "priceUnitCb",
        "priceCurrencyCb",
    }
    return {
        "kind": detail.kind.value,
        "source_url": detail.source_url,
        "name": detail.name,
        "description": detail.description,
        "price_note": detail.price_note,
        "locality": detail.locality.raw,
        "usable_area_m2": detail.usable_area_m2,
        "land_area_m2": detail.land_area_m2,
        "building_area_m2": detail.building_area_m2,
        "floor_area_m2": detail.floor_area_m2,
        "garden_area_m2": detail.garden_area_m2,
        "building_condition_code": detail.building_condition_code,
        "building_type_code": detail.building_type_code,
        "object_type_code": detail.object_type_code,
        "room_count_code": detail.room_count_code,
        "energy_rating_code": detail.energy_rating_code,
        "images": [image.raw for image in detail.images],
        "params": detail.params,
        "source": {key: value for key, value in detail.raw.items() if key not in price_source_keys},
    }


def deactivate_listing(
    session: Session, *, listing: Listing, run: ScrapeRun, occurred_at: datetime
) -> ListingEvent | None:
    """Persist one low-level deactivation; the caller must enforce the complete-run gate."""
    occurred_at = _aware(occurred_at)
    draft = deactivation_event(
        ListingState(
            price_czk=listing.price_czk,
            detail_hash=listing.content_hash,
            is_active=listing.is_active,
        )
    )
    if draft is None:
        return None
    listing.is_active = False
    listing.inactive_at = occurred_at
    listing.updated_at = occurred_at
    return _add_event(session, listing, run, draft, occurred_at)


def deactivate_missing_listings(session: Session, *, run: ScrapeRun, occurred_at: datetime) -> int:
    """Deactivate unseen active listings only behind the complete-success gate."""
    if (
        run.status is not ScrapeRunStatus.SUCCEEDED
        or not run.chata_complete
        or not run.chalupa_complete
        or run.finished_at is None
    ):
        raise DeactivationSafetyError(
            "bulk deactivation requires a finished successful run with both categories complete"
        )
    observed_in_run = (
        select(ListingObservation.id)
        .where(
            ListingObservation.run_id == run.id,
            ListingObservation.listing_id == Listing.id,
        )
        .exists()
    )
    missing = list(
        session.scalars(
            select(Listing).where(Listing.is_active, ~observed_in_run).with_for_update()
        )
    )
    count = 0
    for listing in missing:
        if (
            deactivate_listing(session, listing=listing, run=run, occurred_at=occurred_at)
            is not None
        ):
            count += 1
    return count


def _add_event(
    session: Session,
    listing: Listing,
    run: ScrapeRun,
    draft: EventDraft,
    occurred_at: datetime,
) -> ListingEvent:
    event = ListingEvent(
        listing_id=listing.id,
        run_id=run.id,
        event_type=draft.event_type,
        occurred_at=occurred_at,
        old_price_czk=draft.old_price_czk,
        new_price_czk=draft.new_price_czk,
        changes_json=draft.changes or {},
    )
    session.add(event)
    return event


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("pipeline clock must return a timezone-aware datetime")
    return value


def _run_result(run: ScrapeRun) -> RunResult:
    return RunResult(
        run_id=run.id,
        logical_key=run.logical_key,
        status=run.status,
        found_count=run.found_count,
        new_count=run.new_count,
        changed_count=run.changed_count,
        error_count=run.error_count,
        deactivated_count=run.deactivated_count,
        chata_complete=run.chata_complete,
        chalupa_complete=run.chalupa_complete,
    )
