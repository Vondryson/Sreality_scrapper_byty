"""FastAPI application factory with explicit dependency wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from sreality_tracker import __version__
from sreality_tracker.api.dependencies import AppContainer
from sreality_tracker.api.errors import register_exception_handlers
from sreality_tracker.api.listing_insights import router as listing_insights_router
from sreality_tracker.api.listings import router as listings_router
from sreality_tracker.api.system import router as system_router
from sreality_tracker.api.user_listing_service import ImageArchiver
from sreality_tracker.api.user_listings import router as user_listings_router
from sreality_tracker.core.settings import Settings, load_settings
from sreality_tracker.db.session import create_database_engine, create_session_factory
from sreality_tracker.storage.images import HttpxImageFetcher, LocalImageArchiveStorage

API_V1_PREFIX = "/api/v1"


def create_app(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    readiness_probe: Callable[[], bool] | None = None,
    image_archiver: ImageArchiver | None = None,
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
        image_archiver=image_archiver or _local_image_archiver(resolved_settings),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
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
    app.include_router(listings_router, prefix=API_V1_PREFIX)
    app.include_router(listing_insights_router, prefix=API_V1_PREFIX)
    app.include_router(user_listings_router, prefix=API_V1_PREFIX)
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


def _local_image_archiver(settings: Settings) -> ImageArchiver:
    return ImageArchiver(
        fetcher=HttpxImageFetcher(timeout_seconds=settings.http_timeout_seconds),
        storage=LocalImageArchiveStorage(settings.raw_storage_path / "images"),
    )
