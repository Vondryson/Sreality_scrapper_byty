import os

import pytest

from sreality_tracker.distances.air import Coordinates
from sreality_tracker.distances.routes import RoutesClient


@pytest.mark.live
def test_google_routes_compute_route_live() -> None:
    if os.getenv("SREALITY_RUN_ROUTES_LIVE_TESTS") != "1":
        pytest.skip("Set SREALITY_RUN_ROUTES_LIVE_TESTS=1 for the one-request Routes check")
    project_id = os.getenv("SREALITY_ROUTES_PROJECT_ID")
    access_token = os.getenv("SREALITY_ROUTES_ACCESS_TOKEN")
    if not project_id or not access_token:
        pytest.skip("Routes project ID and short-lived access token are required")

    with RoutesClient(
        project_id=project_id,
        access_token_provider=lambda: access_token,
        max_attempts=1,
        request_limit=1,
    ) as client:
        result = client.compute_route(
            origin=Coordinates(50.0871072, 14.4178281),
            destination=Coordinates(49.1951, 16.6068),
        )

    assert 180_000 <= result.distance_meters <= 260_000
    assert 5_400 <= result.duration_seconds <= 14_400
    assert client.request_count == 1
