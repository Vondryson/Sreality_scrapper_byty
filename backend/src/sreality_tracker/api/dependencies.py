"""Application container and request-scoped dependencies."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sreality_tracker.core.settings import Settings

if False:  # pragma: no cover - imported only for static typing without a runtime cycle
    from sreality_tracker.api.auth import AuthManager
    from sreality_tracker.api.user_listing_service import ImageArchiver


@dataclass(frozen=True, slots=True)
class AppContainer:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    readiness_probe: Callable[[], bool]
    owns_engine: bool
    image_archiver: ImageArchiver | None
    auth_manager: AuthManager | None
    manual_scrape_trigger: Callable[[str], None] | None


def get_container(request: Request) -> AppContainer:
    container: AppContainer = request.app.state.container
    return container


def get_session(
    container: Annotated[AppContainer, Depends(get_container)],
) -> Iterator[Session]:
    with container.session_factory() as session:
        yield session


def get_readiness_probe(
    container: Annotated[AppContainer, Depends(get_container)],
) -> Callable[[], bool]:
    return container.readiness_probe


DatabaseSession = Annotated[Session, Depends(get_session)]
ApplicationContainer = Annotated[AppContainer, Depends(get_container)]
