"""Liveness and readiness endpoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from sreality_tracker.api.contracts import ErrorResponse, HealthResponse
from sreality_tracker.api.dependencies import get_readiness_probe
from sreality_tracker.api.errors import ApiError

router = APIRouter(prefix="/health", tags=["system"])


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse}},
)
def readiness(
    probe: Annotated[Callable[[], bool], Depends(get_readiness_probe)],
) -> HealthResponse:
    if not probe():
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Service is not ready",
        )
    return HealthResponse(status="ready")
