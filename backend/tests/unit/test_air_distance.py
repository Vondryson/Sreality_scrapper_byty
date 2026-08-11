from __future__ import annotations

import pytest

from sreality_tracker.distances.air import (
    Coordinates,
    haversine_distance_km,
    optional_coordinates,
)
from sreality_tracker.domain.reference_points import PRAGUE_CENTER_V1


def test_haversine_is_zero_for_same_point_and_symmetric() -> None:
    prague = Coordinates(PRAGUE_CENTER_V1.latitude, PRAGUE_CENTER_V1.longitude)
    brno = Coordinates(49.1951, 16.6068)

    assert haversine_distance_km(prague, prague) == 0.0
    assert haversine_distance_km(prague, brno) == pytest.approx(
        haversine_distance_km(brno, prague), abs=1e-12
    )


def test_prague_to_brno_distance_matches_known_geodetic_range() -> None:
    prague = Coordinates(PRAGUE_CENTER_V1.latitude, PRAGUE_CENTER_V1.longitude)
    brno = Coordinates(49.1951, 16.6068)

    assert haversine_distance_km(prague, brno) == pytest.approx(186.221, abs=0.001)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (None, 14.0),
        (50.0, None),
        (91.0, 14.0),
        (50.0, float("inf")),
    ],
)
def test_optional_coordinates_reject_missing_or_invalid_gps(
    latitude: float | None, longitude: float | None
) -> None:
    assert optional_coordinates(latitude, longitude) is None


def test_coordinate_hash_is_stable_at_documented_precision() -> None:
    first = Coordinates(50.12345671, 14.12345671)
    below_precision = Coordinates(50.123456714, 14.123456714)
    moved = Coordinates(50.1234568, 14.1234567)

    assert first.coordinate_hash == below_precision.coordinate_hash
    assert first.coordinate_hash != moved.coordinate_hash
