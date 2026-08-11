from __future__ import annotations

import json
import os
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from sreality_tracker.db.models import (
    Listing,
    ListingEvent,
    ListingImage,
    ListingObservation,
    ScrapeRun,
    ScrapeRunStatus,
    ScrapeRunTrigger,
)
from sreality_tracker.db.session import create_database_engine, create_session_factory
from sreality_tracker.domain.events import ListingEventType
from sreality_tracker.domain.listings import ListingDetail, ListingKind
from sreality_tracker.scraper.parser import parse_detail_fixture
from sreality_tracker.scraper.pipeline import ScrapePipeline, deactivate_listing
from sreality_tracker.scraper.source import FetchedListing
from sreality_tracker.storage.raw import LocalRawStorage

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "sreality"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def migration_config(database_url: str) -> Config:
    config = Config(REPOSITORY_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["database_url"] = database_url
    config.attributes["expected_database"] = "sreality_tracker_test"
    return config


def load_detail(filename: str, sreality_id: int) -> ListingDetail:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / filename).read_text(encoding="utf-8"))
    return parse_detail_fixture(
        payload,
        sreality_id=sreality_id,
        source_url=f"https://www.sreality.cz/detail/fixture/{sreality_id}",
    )


class FakeSource:
    def __init__(self, details: dict[ListingKind, tuple[ListingDetail, ...]]) -> None:
        self.details = details
        self.calls: list[ListingKind] = []

    def iter_kind(self, kind: ListingKind) -> Iterator[FetchedListing]:
        self.calls.append(kind)
        for detail in self.details[kind]:
            yield FetchedListing(detail)


class FailingSource(FakeSource):
    def __init__(
        self,
        details: dict[ListingKind, tuple[ListingDetail, ...]],
        *,
        failing_kind: ListingKind,
    ) -> None:
        super().__init__(details)
        self.failing_kind = failing_kind

    def iter_kind(self, kind: ListingKind) -> Iterator[FetchedListing]:
        if kind is self.failing_kind:
            self.calls.append(kind)
            raise RuntimeError("simulated category failure")
        yield from super().iter_kind(kind)


class AdvancingClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 8, 11, 10, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


@pytest.mark.integration
def test_pipeline_upserts_state_and_keeps_one_observation_per_run(tmp_path: Path) -> None:
    database_url = os.getenv("SREALITY_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("SREALITY_TEST_DATABASE_URL is not configured")
    assert make_url(database_url).database == "sreality_tracker_test"
    command.upgrade(migration_config(database_url), "head")

    engine = create_database_engine(database_url)
    factory = create_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE listing_distances, user_listing_data, listing_events, "
                "listing_images, listing_observations, listings, scrape_runs "
                "RESTART IDENTITY CASCADE"
            )
        )

    chata = load_detail("detail_chata.json", 1001)
    chalupa = load_detail("detail_chalupa.json", 2001)
    first_source = FakeSource({ListingKind.CHATA: (chata, chata), ListingKind.CHALUPA: (chalupa,)})
    storage = LocalRawStorage(tmp_path / "raw")
    clock = AdvancingClock()
    first_pipeline = ScrapePipeline(
        session_factory=factory,
        source=first_source,
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    )

    first = first_pipeline.execute(logical_key="manual:fixture:first")
    repeated = first_pipeline.execute(logical_key="manual:fixture:first")

    assert first == repeated
    assert first.status.value == "succeeded"
    assert (first.found_count, first.new_count, first.changed_count, first.error_count) == (
        2,
        2,
        0,
        0,
    )
    assert first.chata_complete and first.chalupa_complete
    assert first_source.calls == [ListingKind.CHATA, ListingKind.CHALUPA]

    changed_raw = deepcopy(chata.raw)
    changed_raw["priceCzk"] = (chata.price.price_czk or 0) + 100_000
    changed_price = replace(
        chata.price,
        source_price_czk=changed_raw["priceCzk"],
        price_czk=changed_raw["priceCzk"],
    )
    changed_chata = replace(chata, price=changed_price, raw=changed_raw)
    second_source = FakeSource(
        {ListingKind.CHATA: (changed_chata,), ListingKind.CHALUPA: (chalupa,)}
    )
    second = ScrapePipeline(
        session_factory=factory,
        source=second_source,
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:fixture:second")

    assert (second.found_count, second.new_count, second.changed_count) == (2, 0, 1)

    deactivated_at = clock()
    with factory.begin() as session:
        stored_chata = session.scalar(
            select(Listing).where(Listing.sreality_id == 1001).with_for_update()
        )
        assert stored_chata is not None
        deactivation_run = ScrapeRun(
            logical_key="manual:fixture:deactivation",
            trigger=ScrapeRunTrigger.MANUAL,
            status=ScrapeRunStatus.PARTIAL,
            started_at=deactivated_at,
            finished_at=deactivated_at,
            scraper_version="test-v1",
        )
        session.add(deactivation_run)
        session.flush()
        event = deactivate_listing(
            session,
            listing=stored_chata,
            run=deactivation_run,
            occurred_at=deactivated_at,
        )
        assert event is not None

    returned_raw = deepcopy(chata.raw)
    returned_raw["description"] = "changed description"
    returned_chata = replace(chata, description="changed description", raw=returned_raw)
    third = ScrapePipeline(
        session_factory=factory,
        source=FakeSource({ListingKind.CHATA: (returned_chata,), ListingKind.CHALUPA: (chalupa,)}),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:fixture:third")

    assert (third.found_count, third.new_count, third.changed_count) == (2, 0, 1)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ScrapeRun)) == 4
        assert session.scalar(select(func.count()).select_from(Listing)) == 2
        assert session.scalar(select(func.count()).select_from(ListingObservation)) == 6
        image_count = session.scalar(select(func.count()).select_from(ListingImage))
        assert image_count is not None and image_count > 0
        stored_chata = session.scalar(select(Listing).where(Listing.sreality_id == 1001))
        assert stored_chata is not None
        assert stored_chata.price_czk == chata.price.price_czk
        assert stored_chata.description == "changed description"
        assert stored_chata.is_active
        event_types = session.scalars(
            select(ListingEvent.event_type).order_by(ListingEvent.id)
        ).all()
        assert event_types == [
            ListingEventType.CREATED,
            ListingEventType.CREATED,
            ListingEventType.PRICE_INCREASED,
            ListingEventType.DEACTIVATED,
            ListingEventType.REACTIVATED,
            ListingEventType.PRICE_DECREASED,
            ListingEventType.DETAILS_CHANGED,
        ]
        raw_keys = session.scalars(select(ListingObservation.raw_object_key)).all()
        assert len(set(raw_keys)) == 6
        assert all(key is not None and storage.load_json(key) for key in raw_keys)

    engine.dispose()


@pytest.mark.integration
def test_partial_run_never_deactivates_but_complete_run_does(tmp_path: Path) -> None:
    database_url = os.getenv("SREALITY_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("SREALITY_TEST_DATABASE_URL is not configured")
    assert make_url(database_url).database == "sreality_tracker_test"
    command.upgrade(migration_config(database_url), "head")

    engine = create_database_engine(database_url)
    factory = create_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE listing_distances, user_listing_data, listing_events, "
                "listing_images, listing_observations, listings, scrape_runs "
                "RESTART IDENTITY CASCADE"
            )
        )

    chata = load_detail("detail_chata.json", 3001)
    omitted_chata = replace(chata, sreality_id=3002, source_url="https://example.invalid/3002")
    chalupa = load_detail("detail_chalupa.json", 4001)
    clock = AdvancingClock()
    storage = LocalRawStorage(tmp_path / "raw")

    baseline = ScrapePipeline(
        session_factory=factory,
        source=FakeSource(
            {
                ListingKind.CHATA: (chata, omitted_chata),
                ListingKind.CHALUPA: (chalupa,),
            }
        ),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:gate:baseline")
    assert baseline.status is ScrapeRunStatus.SUCCEEDED
    assert baseline.deactivated_count == 0

    partial = ScrapePipeline(
        session_factory=factory,
        source=FailingSource(
            {ListingKind.CHATA: (chata,), ListingKind.CHALUPA: ()},
            failing_kind=ListingKind.CHALUPA,
        ),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:gate:partial")
    assert partial.status is ScrapeRunStatus.PARTIAL
    assert partial.chata_complete and not partial.chalupa_complete
    assert partial.deactivated_count == 0

    with factory() as session:
        active_ids = set(session.scalars(select(Listing.sreality_id).where(Listing.is_active)))
        assert active_ids == {3001, 3002, 4001}

    complete = ScrapePipeline(
        session_factory=factory,
        source=FakeSource({ListingKind.CHATA: (chata,), ListingKind.CHALUPA: (chalupa,)}),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:gate:complete")
    assert complete.status is ScrapeRunStatus.SUCCEEDED
    assert complete.deactivated_count == 1

    with factory() as session:
        missing = session.scalar(select(Listing).where(Listing.sreality_id == 3002))
        assert missing is not None
        assert not missing.is_active
        assert missing.inactive_at is not None
        deactivation_runs = session.scalars(
            select(ScrapeRun.logical_key)
            .join(ListingEvent, ListingEvent.run_id == ScrapeRun.id)
            .where(ListingEvent.event_type == ListingEventType.DEACTIVATED)
        ).all()
        assert deactivation_runs == ["manual:gate:complete"]

    engine.dispose()


@pytest.mark.integration
def test_listing_transaction_rolls_back_on_invalid_persisted_detail(tmp_path: Path) -> None:
    database_url = os.getenv("SREALITY_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("SREALITY_TEST_DATABASE_URL is not configured")
    assert make_url(database_url).database == "sreality_tracker_test"
    command.upgrade(migration_config(database_url), "head")

    engine = create_database_engine(database_url)
    factory = create_session_factory(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE listing_distances, user_listing_data, listing_events, "
                "listing_images, listing_observations, listings, scrape_runs "
                "RESTART IDENTITY CASCADE"
            )
        )

    chata = load_detail("detail_chata.json", 5001)
    invalid_image = replace(chata.images[0], width=0)
    invalid_chata = replace(chata, images=(invalid_image,))
    chalupa = load_detail("detail_chalupa.json", 6001)
    result = ScrapePipeline(
        session_factory=factory,
        source=FakeSource({ListingKind.CHATA: (invalid_chata,), ListingKind.CHALUPA: (chalupa,)}),
        raw_storage=LocalRawStorage(tmp_path / "raw"),
        scraper_version="test-v1",
        clock=AdvancingClock(),
    ).execute(logical_key="manual:rollback")

    assert result.status is ScrapeRunStatus.PARTIAL
    assert result.error_count == 1
    assert not result.chata_complete and result.chalupa_complete
    assert result.deactivated_count == 0
    with factory() as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Listing).where(Listing.sreality_id == 5001)
            )
            == 0
        )
        assert (
            session.scalar(select(func.count()).select_from(ListingObservation).join(Listing)) == 1
        )
        assert session.scalar(select(Listing.sreality_id)) == 6001
        assert session.scalar(select(func.count()).select_from(ListingEvent)) == 1

    engine.dispose()
