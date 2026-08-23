import json
from decimal import Decimal

import httpx
import pytest

from sreality_tracker.distances.air import Coordinates
from sreality_tracker.distances.routes import ROUTES_ENDPOINT, RoutesClient, RoutesError


def test_compute_routes_uses_minimal_essentials_contract_and_retries() -> None:
    requests: list[httpx.Request] = []
    statuses = iter([503, 200])

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        status = next(statuses)
        if status == 503:
            return httpx.Response(status, json={"error": "temporary"})
        return httpx.Response(
            status,
            json={"routes": [{"distanceMeters": 207_588, "duration": "8233s"}]},
        )

    sleeps: list[float] = []
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = RoutesClient(
            project_id="sreality-scrapper-504307",
            access_token_provider=lambda: "short-lived-token",
            client=http_client,
            sleep=sleeps.append,
            random_uniform=lambda _start, _end: 0.0,
        )
        result = client.compute_route(
            origin=Coordinates(50.0871072, 14.4178281),
            destination=Coordinates(49.1951, 16.6068),
        )

    assert result.distance_meters == 207_588
    assert result.duration_seconds == Decimal(8233)
    assert client.request_count == 2
    assert sleeps == [0.5]
    assert all(str(request.url) == ROUTES_ENDPOINT for request in requests)
    assert all(
        request.headers["x-goog-user-project"] == "sreality-scrapper-504307" for request in requests
    )
    assert all(
        request.headers["x-goog-fieldmask"] == "routes.distanceMeters,routes.duration"
        for request in requests
    )
    payload = json.loads(requests[-1].content)
    assert payload["travelMode"] == "DRIVE"
    assert payload["routingPreference"] == "TRAFFIC_UNAWARE"
    assert payload["computeAlternativeRoutes"] is False
    assert "departureTime" not in payload


def test_non_retryable_rejection_is_safe_and_not_retried() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(403, json={"secret": "x"}))
    with httpx.Client(transport=transport) as http_client:
        client = RoutesClient(
            project_id="test-project",
            access_token_provider=lambda: "token",
            client=http_client,
        )
        with pytest.raises(RoutesError, match="rejected") as captured:
            client.compute_route(
                origin=Coordinates(50.0, 14.0),
                destination=Coordinates(49.0, 16.0),
            )

    assert "secret" not in str(captured.value)
    assert client.request_count == 1


def test_client_never_exceeds_its_process_request_budget() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(503))
    with httpx.Client(transport=transport) as http_client:
        client = RoutesClient(
            project_id="test-project",
            access_token_provider=lambda: "token",
            client=http_client,
            max_attempts=3,
            request_limit=1,
            sleep=lambda _delay: None,
        )
        with pytest.raises(RoutesError, match="budget"):
            client.compute_route(
                origin=Coordinates(50.0, 14.0),
                destination=Coordinates(49.0, 16.0),
            )

    assert client.request_count == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"routes": []},
        {"routes": [{"distanceMeters": -1, "duration": "10s"}]},
        {"routes": [{"distanceMeters": 10, "duration": "invalid"}]},
    ],
)
def test_malformed_route_response_is_rejected(payload: object) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    with httpx.Client(transport=transport) as http_client:
        client = RoutesClient(
            project_id="test-project",
            access_token_provider=lambda: "token",
            client=http_client,
        )
        with pytest.raises(RoutesError):
            client.compute_route(
                origin=Coordinates(50.0, 14.0),
                destination=Coordinates(49.0, 16.0),
            )
