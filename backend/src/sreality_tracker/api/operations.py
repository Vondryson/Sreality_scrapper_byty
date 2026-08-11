"""Owner-only scraper status and idempotent manual trigger endpoints."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from sreality_tracker.api.contracts import ApiModel
from sreality_tracker.api.dependencies import ApplicationContainer, DatabaseSession
from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.owner import AuthenticatedOwner
from sreality_tracker.db.models import ScrapeRun, ScrapeRunStatus, ScrapeRunTrigger

router = APIRouter(prefix="/operations", tags=["operations"])


class ManualRunRequest(ApiModel):
    logical_key: str = Field(min_length=1, max_length=153, pattern=r"^[A-Za-z0-9:._-]+$")


class ScrapeRunResponse(ApiModel):
    run_id: UUID
    logical_key: str
    status: ScrapeRunStatus
    trigger: ScrapeRunTrigger
    started_at: datetime
    finished_at: datetime | None
    found_count: int
    new_count: int
    changed_count: int
    error_count: int
    deactivated_count: int


@router.get("/scrape-runs/latest", response_model=ScrapeRunResponse)
def latest_scrape_run(
    session: DatabaseSession,
    _owner: AuthenticatedOwner,
) -> ScrapeRunResponse:
    run = session.scalar(
        select(ScrapeRun).order_by(ScrapeRun.started_at.desc(), ScrapeRun.id.desc()).limit(1)
    )
    if run is None:
        raise ApiError(status_code=404, code="scrape_run_not_found", message="No scrape run exists")
    return _run_response(run)


@router.post(
    "/scrape-runs",
    response_model=ScrapeRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_scrape_run(
    request: ManualRunRequest,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    container: ApplicationContainer,
    _owner: AuthenticatedOwner,
) -> ScrapeRunResponse:
    trigger = container.manual_scrape_trigger
    if trigger is None:
        raise ApiError(
            status_code=503,
            code="manual_trigger_unavailable",
            message="Manual trigger is unavailable",
        )
    logical_key = f"manual:{request.logical_key}"
    run = session.scalar(select(ScrapeRun).where(ScrapeRun.logical_key == logical_key))
    if run is None:
        run = ScrapeRun(
            logical_key=logical_key,
            trigger=ScrapeRunTrigger.MANUAL,
            status=ScrapeRunStatus.RUNNING,
            started_at=datetime.now(UTC),
            scraper_version="api-trigger",
        )
        session.add(run)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            run = session.scalar(select(ScrapeRun).where(ScrapeRun.logical_key == logical_key))
            if run is None:
                raise
        else:
            session.refresh(run)
            background_tasks.add_task(
                _execute_trigger,
                container.session_factory,
                trigger,
                run.id,
                logical_key,
            )
    return _run_response(run)


def _execute_trigger(
    session_factory: sessionmaker[Session],
    trigger: Callable[[str], None],
    run_id: UUID,
    logical_key: str,
) -> None:
    try:
        trigger(logical_key)
    except Exception as error:
        with session_factory.begin() as session:
            run = session.get(ScrapeRun, run_id)
            if run is not None and run.status is ScrapeRunStatus.RUNNING:
                run.status = ScrapeRunStatus.FAILED
                run.finished_at = datetime.now(UTC)
                run.error_code = "manual_trigger_failed"
                run.error_summary = f"error_type:{type(error).__name__}"


def _run_response(run: ScrapeRun) -> ScrapeRunResponse:
    return ScrapeRunResponse(
        run_id=run.id,
        logical_key=run.logical_key,
        status=run.status,
        trigger=run.trigger,
        started_at=run.started_at,
        finished_at=run.finished_at,
        found_count=run.found_count,
        new_count=run.new_count,
        changed_count=run.changed_count,
        error_count=run.error_count,
        deactivated_count=run.deactivated_count,
    )
