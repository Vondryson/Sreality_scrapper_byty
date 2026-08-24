"""Minimal resilient Google Routes Compute Routes client."""

from __future__ import annotations

import logging
import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from sreality_tracker.distances.air import Coordinates

ROUTES_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
ROUTES_FIELD_MASK = "routes.distanceMeters,routes.duration"
_DURATION_PATTERN = re.compile(r"^(?P<seconds>\d+(?:\.\d+)?)s$")
logger = logging.getLogger(__name__)


class RoutesError(RuntimeError):
    """Safe base error for Google Routes failures."""


class RoutesResponseError(RoutesError):
    """The provider returned a malformed or unusable response."""


@dataclass(frozen=True, slots=True)
class RouteResult:
    distance_meters: int
    duration_seconds: Decimal


class RoutesClient:
    """Call only the Essentials Compute Routes shape used by the tracker."""

    def __init__(
        self,
        *,
        project_id: str,
        access_token_provider: Callable[[], str],
        timeout_seconds: float = 20.0,
        max_attempts: int = 3,
        request_limit: int | None = None,
        backoff_base_seconds: float = 0.5,
        jitter_max_seconds: float = 0.25,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        random_uniform: Callable[[float, float], float] = random.uniform,
    ) -> None:
        if not project_id.strip():
            raise ValueError("project_id must not be empty")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if request_limit is not None and request_limit < 1:
            raise ValueError("request_limit must be positive")
        self._project_id = project_id
        self._access_token_provider = access_token_provider
        self._max_attempts = max_attempts
        self._request_limit = request_limit
        self._backoff_base_seconds = backoff_base_seconds
        self._jitter_max_seconds = jitter_max_seconds
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._owns_client = client is None
        self._sleep = sleep
        self._random_uniform = random_uniform
        self.request_count = 0

    def __enter__(self) -> RoutesClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def compute_route(self, *, origin: Coordinates, destination: Coordinates) -> RouteResult:
        payload = {
            "origin": {"location": {"latLng": _lat_lng(origin)}},
            "destination": {"location": {"latLng": _lat_lng(destination)}},
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_UNAWARE",
            "computeAlternativeRoutes": False,
            "languageCode": "cs-CZ",
            "units": "METRIC",
        }
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                token = self._access_token_provider().strip()
                if not token:
                    raise RoutesError("OAuth access token is unavailable")
                if self._request_limit is not None and self.request_count >= self._request_limit:
                    raise RoutesError("Routes request budget is exhausted")
                self.request_count += 1
                logger.info(
                    "Google Routes request",
                    extra={"event": "routes_request", "step": "provider_call"},
                )
                response = self._client.post(
                    ROUTES_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Goog-User-Project": self._project_id,
                        "X-Goog-FieldMask": ROUTES_FIELD_MASK,
                    },
                    json=payload,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise _RetryableRoutesError("transient Routes response")
                response.raise_for_status()
                return _parse_response(response.json())
            except (_RetryableRoutesError, httpx.TransportError) as error:
                last_error = error
                if attempt == self._max_attempts:
                    break
                logger.warning(
                    "Retrying Google Routes request",
                    extra={
                        "event": "routes_retry",
                        "step": type(error).__name__,
                    },
                )
                delay = self._backoff_base_seconds * (2 ** (attempt - 1))
                delay += self._random_uniform(0.0, self._jitter_max_seconds)
                self._sleep(delay)
            except httpx.HTTPStatusError as error:
                raise RoutesError("Routes request was rejected") from error
            except (ValueError, TypeError) as error:
                raise RoutesResponseError("Routes response is not valid JSON") from error
        raise RoutesError("Routes request failed after retries") from last_error


class _RetryableRoutesError(RoutesError):
    pass


def _lat_lng(coordinates: Coordinates) -> dict[str, float]:
    return {"latitude": coordinates.latitude, "longitude": coordinates.longitude}


def _parse_response(payload: Any) -> RouteResult:
    if not isinstance(payload, dict):
        raise RoutesResponseError("Routes response root is not an object")
    routes = payload.get("routes")
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
        raise RoutesResponseError("Routes response does not contain a route")
    route = routes[0]
    distance = route.get("distanceMeters")
    duration = route.get("duration")
    if not isinstance(distance, int) or isinstance(distance, bool) or distance < 0:
        raise RoutesResponseError("Routes distance is invalid")
    if not isinstance(duration, str):
        raise RoutesResponseError("Routes duration is invalid")
    match = _DURATION_PATTERN.fullmatch(duration)
    if match is None:
        raise RoutesResponseError("Routes duration has an invalid format")
    try:
        seconds = Decimal(match.group("seconds"))
    except InvalidOperation as error:
        raise RoutesResponseError("Routes duration is invalid") from error
    return RouteResult(distance_meters=distance, duration_seconds=seconds)
