from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterator
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from sreality_tracker.api.app import create_app
from sreality_tracker.api.listing_contracts import (
    ListingFilters,
    ListingSort,
    ListingStatusFilter,
)
from sreality_tracker.api.listing_insight_repository import (
    get_listing_detail,
    get_listing_history,
    get_price_medians,
    list_map_listings,
)
from sreality_tracker.api.listing_repository import list_listings
from sreality_tracker.api.user_listing_contracts import UserListingUpdate
from sreality_tracker.api.user_listing_service import ImageArchiver, update_user_listing
from sreality_tracker.core.settings import Environment, Settings
from sreality_tracker.db.models import (
    Listing,
    ListingDistance,
    ListingEvent,
    ListingImage,
    ListingObservation,
    ScrapeRun,
    ScrapeRunStatus,
    ScrapeRunTrigger,
    UserListingData,
)
from sreality_tracker.db.session import create_database_engine, create_session_factory
from sreality_tracker.distances.road import RoadDistanceEnricher
from sreality_tracker.distances.routes import RoutesClient
from sreality_tracker.domain.events import ListingEventType
from sreality_tracker.domain.listings import ListingDetail, ListingKind
from sreality_tracker.scraper.parser import parse_detail_fixture
from sreality_tracker.scraper.pipeline import ScrapePipeline, deactivate_listing
from sreality_tracker.scraper.source import FetchedListing
from sreality_tracker.storage.images import (
    FetchedImage,
    ImageArchiveError,
    LocalImageArchiveStorage,
)
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


class FakeImageFetcher:
    def __init__(self, *, failing_urls: set[str] | None = None) -> None:
        self.failing_urls = failing_urls or set()
        self.calls: list[str] = []

    def fetch(self, source_url: str) -> FetchedImage:
        self.calls.append(source_url)
        if source_url in self.failing_urls:
            raise ImageArchiveError("simulated image failure")
        return FetchedImage(content=f"image:{source_url}".encode(), content_type="image/jpeg")


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
        assert session.scalar(select(func.count()).select_from(ListingDistance)) == 2
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
def test_listing_repository_filters_sorts_and_paginates(tmp_path: Path) -> None:
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

    chata = load_detail("detail_chata.json", 7001)
    chata_price = replace(chata.price, source_price_czk=1_000_000, price_czk=1_000_000)
    chata_locality = replace(chata.locality, region="Jihočeský kraj", district="Tábor")
    chata = replace(chata, price=chata_price, locality=chata_locality)
    chalupa = load_detail("detail_chalupa.json", 8001)
    chalupa_price = replace(chalupa.price, source_price_czk=2_000_000, price_czk=2_000_000)
    chalupa_locality = replace(chalupa.locality, region="Středočeský kraj", district="Příbram")
    chalupa = replace(chalupa, price=chalupa_price, locality=chalupa_locality)

    result = ScrapePipeline(
        session_factory=factory,
        source=FakeSource({ListingKind.CHATA: (chata,), ListingKind.CHALUPA: (chalupa,)}),
        raw_storage=LocalRawStorage(tmp_path / "raw"),
        scraper_version="test-v1",
        clock=AdvancingClock(),
    ).execute(logical_key="manual:list-api")
    assert result.status is ScrapeRunStatus.SUCCEEDED

    with factory.begin() as session:
        favorite_listing = session.scalar(select(Listing).where(Listing.sreality_id == 8001))
        assert favorite_listing is not None
        session.add(UserListingData(listing_id=favorite_listing.id, is_favorite=True))

    with factory() as session:
        first_page = list_listings(
            session,
            ListingFilters(
                status=ListingStatusFilter.ALL,
                page_size=1,
                sort=ListingSort.PRICE_ASC,
            ),
        )
        assert first_page.total == 2
        assert first_page.pages == 2
        assert [item.sreality_id for item in first_page.items] == [7001]

        filtered = list_listings(
            session,
            ListingFilters(
                status=ListingStatusFilter.NEW,
                kind=ListingKind.CHALUPA,
                region="Středočeský kraj",
                price_min=1_500_000,
                favorite=True,
                air_distance_max_km=1_000,
            ),
        )
        assert filtered.total == 1
        assert filtered.items[0].sreality_id == 8001
        assert filtered.items[0].is_favorite
        assert filtered.items[0].air_distance_km is not None

    engine.dispose()


@pytest.mark.integration
def test_pipeline_caches_routes_and_provider_failure_never_blocks_listing(tmp_path: Path) -> None:
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

    chata = load_detail("detail_chata.json", 7301)
    chalupa = load_detail("detail_chalupa.json", 8301)
    successful_transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={"routes": [{"distanceMeters": 207_588, "duration": "8233s"}]},
        )
    )
    with httpx.Client(transport=successful_transport) as http_client:
        routes_client = RoutesClient(
            project_id="test-project",
            access_token_provider=lambda: "token",
            client=http_client,
        )
        pipeline = ScrapePipeline(
            session_factory=factory,
            source=FakeSource({ListingKind.CHATA: (chata,), ListingKind.CHALUPA: (chalupa,)}),
            raw_storage=LocalRawStorage(tmp_path / "raw"),
            scraper_version="test-v1",
            road_distance_enricher=RoadDistanceEnricher(
                session_factory=factory,
                client=routes_client,
            ),
            clock=AdvancingClock(),
        )
        first = pipeline.execute(logical_key="manual:routes:first")
        second = pipeline.execute(logical_key="manual:routes:second")

    assert first.status is ScrapeRunStatus.SUCCEEDED
    assert second.status is ScrapeRunStatus.SUCCEEDED
    assert routes_client.request_count == 2
    with factory() as session:
        road_rows = session.scalars(
            select(ListingDistance).where(ListingDistance.provider == "google_routes")
        ).all()
        assert len(road_rows) == 2
        assert {float(row.road_distance_km or 0) for row in road_rows} == {207.588}
        assert {row.drive_duration_minutes for row in road_rows} == {138}

    new_chata = replace(chata, sreality_id=7302, source_url="https://example.invalid/7302")
    failing_transport = httpx.MockTransport(lambda _request: httpx.Response(503))
    with httpx.Client(transport=failing_transport) as http_client:
        failing_client = RoutesClient(
            project_id="test-project",
            access_token_provider=lambda: "token",
            client=http_client,
            max_attempts=1,
        )
        failure_result = ScrapePipeline(
            session_factory=factory,
            source=FakeSource(
                {ListingKind.CHATA: (new_chata,), ListingKind.CHALUPA: (chalupa,)}
            ),
            raw_storage=LocalRawStorage(tmp_path / "raw"),
            scraper_version="test-v1",
            road_distance_enricher=RoadDistanceEnricher(
                session_factory=factory,
                client=failing_client,
            ),
            clock=AdvancingClock(),
        ).execute(logical_key="manual:routes:failure")

    assert failure_result.status is ScrapeRunStatus.SUCCEEDED
    assert failing_client.request_count == 1
    with factory() as session:
        persisted = session.scalar(select(Listing).where(Listing.sreality_id == 7302))
        assert persisted is not None
        failed_route = session.scalar(
            select(ListingDistance).where(
                ListingDistance.listing_id == persisted.id,
                ListingDistance.provider == "google_routes",
            )
        )
        assert failed_route is None

    engine.dispose()


@pytest.mark.integration
def test_owner_only_operations_are_csrf_protected_and_idempotent() -> None:
    database_url = os.getenv("SREALITY_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("SREALITY_TEST_DATABASE_URL is not configured")
    assert make_url(database_url).database == "sreality_tracker_test"
    command.upgrade(migration_config(database_url), "head")

    engine = create_database_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE listing_distances, user_listing_data, listing_events, "
                "listing_images, listing_observations, listings, scrape_runs "
                "RESTART IDENTITY CASCADE"
            )
        )
    triggered: list[str] = []
    settings = Settings(
        database_url=SecretStr(database_url),
        environment=Environment.TEST,
        google_oauth_client_id="test-client.apps.googleusercontent.com",
        google_oauth_client_secret=SecretStr("oauth-secret"),
        owner_email="owner@example.com",
        session_secret=SecretStr("s" * 32),
    )
    app = create_app(
        settings=settings,
        engine=engine,
        manual_scrape_trigger=triggered.append,
    )
    manager = app.state.container.auth_manager
    assert manager is not None
    csrf = "integration-csrf"
    session_cookie = manager.codec.dumps(
        {
            "purpose": "owner_session",
            "sub": "owner-subject",
            "email": "owner@example.com",
            "csrf": csrf,
            "exp": int(datetime.now(UTC).timestamp()) + 300,
        }
    )
    auth_headers = {
        "Cookie": f"sreality_session={session_cookie}",
        "X-CSRF-Token": csrf,
    }

    async def exercise_api() -> tuple[httpx.Response, ...]:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
            denied = await client.post(
                "/api/v1/operations/scrape-runs",
                json={"logical_key": "ui-test"},
            )
            csrf_denied = await client.post(
                "/api/v1/operations/scrape-runs",
                json={"logical_key": "ui-test"},
                headers={"Cookie": f"sreality_session={session_cookie}"},
            )
            first = await client.post(
                "/api/v1/operations/scrape-runs",
                json={"logical_key": "ui-test"},
                headers=auth_headers,
            )
            repeated = await client.post(
                "/api/v1/operations/scrape-runs",
                json={"logical_key": "ui-test"},
                headers=auth_headers,
            )
            latest = await client.get(
                "/api/v1/operations/scrape-runs/latest",
                headers=auth_headers,
            )
        return denied, csrf_denied, first, repeated, latest

    denied, csrf_denied, first, repeated, latest = asyncio.run(exercise_api())
    assert denied.status_code == 401
    assert csrf_denied.status_code == 403
    assert first.status_code == 202
    assert repeated.status_code == 202
    assert first.json()["run_id"] == repeated.json()["run_id"]
    assert first.json()["logical_key"] == "manual:ui-test"
    assert latest.status_code == 200
    assert latest.json()["run_id"] == first.json()["run_id"]
    assert triggered == ["manual:ui-test"]

    engine.dispose()


@pytest.mark.integration
def test_detail_history_map_and_medians_follow_their_scrape_runs(tmp_path: Path) -> None:
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

    first_chata = load_detail("detail_chata.json", 7101)
    first_chata = replace(
        first_chata,
        price=replace(
            first_chata.price,
            source_price_czk=1_000_000,
            price_czk=1_000_000,
            price_on_request=False,
        ),
        raw={**first_chata.raw, "priceCzk": 1_000_000},
    )
    first_chalupa = load_detail("detail_chalupa.json", 8101)
    first_chalupa = replace(
        first_chalupa,
        price=replace(
            first_chalupa.price,
            source_price_czk=3_000_000,
            price_czk=3_000_000,
            price_on_request=False,
        ),
        raw={**first_chalupa.raw, "priceCzk": 3_000_000},
    )
    clock = AdvancingClock()
    storage = LocalRawStorage(tmp_path / "raw")
    first_run = ScrapePipeline(
        session_factory=factory,
        source=FakeSource(
            {ListingKind.CHATA: (first_chata,), ListingKind.CHALUPA: (first_chalupa,)}
        ),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:insights:first")
    assert first_run.status is ScrapeRunStatus.SUCCEEDED

    second_chata = replace(
        first_chata,
        price=replace(
            first_chata.price,
            source_price_czk=2_000_000,
            price_czk=2_000_000,
        ),
        raw={**first_chata.raw, "priceCzk": 2_000_000},
    )
    second_chalupa = replace(
        first_chalupa,
        price=replace(
            first_chalupa.price,
            source_price_czk=0,
            price_czk=None,
            price_on_request=True,
            source_price_per_sqm_czk=None,
            derived_price_per_sqm_czk=None,
        ),
        raw={**first_chalupa.raw, "priceCzk": 0},
    )
    second_run = ScrapePipeline(
        session_factory=factory,
        source=FakeSource(
            {ListingKind.CHATA: (second_chata,), ListingKind.CHALUPA: (second_chalupa,)}
        ),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:insights:second")
    assert second_run.status is ScrapeRunStatus.SUCCEEDED

    partial_chata = replace(
        second_chata,
        price=replace(
            second_chata.price,
            source_price_czk=100_000_000,
            price_czk=100_000_000,
        ),
        raw={**second_chata.raw, "priceCzk": 100_000_000},
    )
    partial_run = ScrapePipeline(
        session_factory=factory,
        source=FailingSource(
            {ListingKind.CHATA: (partial_chata,), ListingKind.CHALUPA: ()},
            failing_kind=ListingKind.CHALUPA,
        ),
        raw_storage=storage,
        scraper_version="test-v1",
        clock=clock,
    ).execute(logical_key="manual:insights:partial")
    assert partial_run.status is ScrapeRunStatus.PARTIAL

    with factory.begin() as session:
        chata_model = session.scalar(select(Listing).where(Listing.sreality_id == 7101))
        assert chata_model is not None
        session.add(
            UserListingData(
                listing_id=chata_model.id,
                is_favorite=True,
                private_note="Prověřit příjezdovou cestu",
            )
        )

    with factory() as session:
        chata_model = session.scalar(select(Listing).where(Listing.sreality_id == 7101))
        assert chata_model is not None
        detail = get_listing_detail(session, chata_model.id)
        assert detail.sreality_id == 7101
        assert detail.price_czk == 100_000_000
        assert detail.is_favorite
        assert detail.private_note == "Prověřit příjezdovou cestu"
        assert detail.images
        assert detail.air_distance_km is not None

        history = get_listing_history(session, chata_model.id)
        assert [point.run_status for point in history.prices] == [
            "succeeded",
            "succeeded",
            "partial",
        ]
        assert [point.price_czk for point in history.prices] == [
            1_000_000,
            2_000_000,
            100_000_000,
        ]

        map_data = list_map_listings(
            session,
            ListingFilters(status=ListingStatusFilter.ALL, favorite=True),
        )
        assert map_data.total == 1
        assert map_data.items[0].sreality_id == 7101

        medians = get_price_medians(session, ListingFilters())
        assert medians.current_median_price_czk == 100_000_000
        assert medians.current_sample_size == 1
        assert [point.run_id for point in medians.history] == [
            first_run.run_id,
            second_run.run_id,
        ]
        assert [point.median_price_czk for point in medians.history] == [
            2_000_000,
            2_000_000,
        ]
        assert [point.sample_size for point in medians.history] == [2, 1]

        chalupa_medians = get_price_medians(
            session,
            ListingFilters(kind=ListingKind.CHALUPA),
        )
        assert chalupa_medians.current_median_price_czk is None
        assert chalupa_medians.current_sample_size == 0
        assert [point.median_price_czk for point in chalupa_medians.history] == [3_000_000]

    engine.dispose()


@pytest.mark.integration
def test_favorite_note_and_image_archive_are_idempotent_and_retryable(tmp_path: Path) -> None:
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

    chata = load_detail("detail_chata.json", 7201)
    chalupa = load_detail("detail_chalupa.json", 8201)
    result = ScrapePipeline(
        session_factory=factory,
        source=FakeSource({ListingKind.CHATA: (chata,), ListingKind.CHALUPA: (chalupa,)}),
        raw_storage=LocalRawStorage(tmp_path / "raw"),
        scraper_version="test-v1",
        clock=AdvancingClock(),
    ).execute(logical_key="manual:user-data")
    assert result.status is ScrapeRunStatus.SUCCEEDED

    with factory() as session:
        listing = session.scalar(select(Listing).where(Listing.sreality_id == 7201))
        assert listing is not None
        image_urls = session.scalars(
            select(ListingImage.source_url)
            .where(ListingImage.listing_id == listing.id)
            .order_by(ListingImage.position)
        ).all()
        assert image_urls
        first_fetcher = FakeImageFetcher(failing_urls={image_urls[0]})
        storage = LocalImageArchiveStorage(tmp_path / "archive")
        first = update_user_listing(
            session,
            listing_id=listing.id,
            update=UserListingUpdate(
                is_favorite=True,
                private_note="Soukromá poznámka",
            ),
            archiver=ImageArchiver(fetcher=first_fetcher, storage=storage),
        )
        assert first.is_favorite
        assert first.private_note == "Soukromá poznámka"
        assert first.failed_images == 1
        assert first.archived_images == len(image_urls) - 1

        retry_fetcher = FakeImageFetcher()
        retried = update_user_listing(
            session,
            listing_id=listing.id,
            update=UserListingUpdate(is_favorite=True),
            archiver=ImageArchiver(fetcher=retry_fetcher, storage=storage),
        )
        assert retried.failed_images == 0
        assert retried.archived_images == len(image_urls)
        assert retry_fetcher.calls == [image_urls[0]]

        repeated = update_user_listing(
            session,
            listing_id=listing.id,
            update=UserListingUpdate(is_favorite=True),
            archiver=ImageArchiver(fetcher=retry_fetcher, storage=storage),
        )
        assert repeated == retried
        assert retry_fetcher.calls == [image_urls[0]]

        cleared = update_user_listing(
            session,
            listing_id=listing.id,
            update=UserListingUpdate(is_favorite=False, private_note=None),
            archiver=ImageArchiver(fetcher=retry_fetcher, storage=storage),
        )
        assert not cleared.is_favorite
        assert cleared.private_note is None
        assert cleared.archived_images == len(image_urls)
        assert listing.description == chata.description

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
