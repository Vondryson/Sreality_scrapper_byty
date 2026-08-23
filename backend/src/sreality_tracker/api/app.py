"""FastAPI application factory with explicit dependency wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from sreality_tracker import __version__
from sreality_tracker.api.auth import AuthManager, GoogleOAuthClient, SessionCodec
from sreality_tracker.api.auth_routes import router as auth_router
from sreality_tracker.api.dependencies import AppContainer
from sreality_tracker.api.errors import register_exception_handlers
from sreality_tracker.api.job_trigger import cloud_run_job_trigger
from sreality_tracker.api.listing_insights import router as listing_insights_router
from sreality_tracker.api.listings import router as listings_router
from sreality_tracker.api.operations import router as operations_router
from sreality_tracker.api.owner import require_owner
from sreality_tracker.api.system import router as system_router
from sreality_tracker.api.user_listing_service import ImageArchiver
from sreality_tracker.api.user_listings import router as user_listings_router
from sreality_tracker.core.settings import Settings, StorageBackend, load_settings
from sreality_tracker.db.models import ScrapeRunTrigger
from sreality_tracker.db.session import create_database_engine, create_session_factory
from sreality_tracker.storage.images import (
    GcsImageArchiveStorage,
    HttpxImageFetcher,
    ImageArchiveStorage,
    LocalImageArchiveStorage,
)

API_V1_PREFIX = "/api/v1"


def create_app(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    readiness_probe: Callable[[], bool] | None = None,
    image_archiver: ImageArchiver | None = None,
    auth_manager: AuthManager | None = None,
    manual_scrape_trigger: Callable[[str], None] | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings()
    resolved_engine = engine or create_database_engine(resolved_settings.database_url_value())
    owns_engine = engine is None
    probe = readiness_probe or _database_probe(resolved_engine)
    container = AppContainer(
        settings=resolved_settings,
        engine=resolved_engine,
        session_factory=create_session_factory(resolved_engine),
        readiness_probe=probe,
        owns_engine=owns_engine,
        image_archiver=image_archiver or _image_archiver(resolved_settings),
        auth_manager=auth_manager or _auth_manager(resolved_settings),
        manual_scrape_trigger=manual_scrape_trigger or _manual_trigger(resolved_settings),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if container.auth_manager is not None:
                container.auth_manager.oauth_client.close()
            if container.owns_engine:
                container.engine.dispose()

    app = FastAPI(
        title="Sreality Chaty Tracker API",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.container = container
    register_exception_handlers(app)
    app.include_router(system_router, prefix=API_V1_PREFIX)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    owner_dependencies = [Depends(require_owner)]
    app.include_router(
        listings_router,
        prefix=API_V1_PREFIX,
        dependencies=owner_dependencies,
    )
    app.include_router(
        listing_insights_router,
        prefix=API_V1_PREFIX,
        dependencies=owner_dependencies,
    )
    app.include_router(user_listings_router, prefix=API_V1_PREFIX)
    app.include_router(operations_router, prefix=API_V1_PREFIX)
    return app


def _database_probe(engine: Engine) -> Callable[[], bool]:
    def probe() -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True

    return probe


def _image_archiver(settings: Settings) -> ImageArchiver:
    storage: ImageArchiveStorage
    if settings.storage_backend is StorageBackend.GCS:
        assert settings.storage_bucket is not None
        storage = GcsImageArchiveStorage.from_bucket_name(
            settings.storage_bucket,
            project=settings.gcp_project_id,
        )
    else:
        storage = LocalImageArchiveStorage(settings.raw_storage_path / "images")
    return ImageArchiver(
        fetcher=HttpxImageFetcher(timeout_seconds=settings.http_timeout_seconds),
        storage=storage,
    )


def _auth_manager(settings: Settings) -> AuthManager | None:
    if (
        settings.google_oauth_client_id is None
        or settings.google_oauth_client_secret is None
        or settings.owner_email is None
        or settings.session_secret is None
    ):
        return None
    return AuthManager(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret.get_secret_value(),
        redirect_uri=settings.google_oauth_redirect_uri,
        owner_email=settings.owner_email,
        codec=SessionCodec(settings.session_secret.get_secret_value()),
        oauth_client=GoogleOAuthClient(),
    )


def _manual_trigger(settings: Settings) -> Callable[[str], None] | None:
    if settings.environment.value == "production":
        if (
            settings.gcp_project_id is None
            or settings.cloud_run_region is None
            or settings.scraper_job_name is None
        ):
            return None
        return cloud_run_job_trigger(
            project_id=settings.gcp_project_id,
            region=settings.cloud_run_region,
            job_name=settings.scraper_job_name,
        )

    def trigger(logical_key: str) -> None:
        from sreality_tracker.scraper.cli import _run_pipeline

        _run_pipeline(settings, logical_key=logical_key, trigger=ScrapeRunTrigger.MANUAL)

    return trigger
