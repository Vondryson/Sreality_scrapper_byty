from __future__ import annotations

from dataclasses import replace

import pytest

from sreality_tracker.domain.reference_points import (
    DEFAULT_REFERENCE_POINT_KEY,
    PRAGUE_CENTER_V1,
    REFERENCE_POINTS,
    ReferencePoint,
    ReferencePointNotFoundError,
    get_reference_point,
)


def test_prague_reference_point_is_central_versioned_configuration() -> None:
    point = get_reference_point()

    assert point is PRAGUE_CENTER_V1
    assert DEFAULT_REFERENCE_POINT_KEY == "praha_marianske_namesti"
    assert point.version == 1
    assert point.latitude == 50.0871072
    assert point.longitude == 14.4178281
    assert point.cache_identity == (point.key, point.version, point.coordinate_hash)
    assert len(point.coordinate_hash) == 64


def test_coordinate_hash_changes_when_coordinates_change() -> None:
    moved = replace(PRAGUE_CENTER_V1, version=2, latitude=50.0872072)

    assert moved.coordinate_hash != PRAGUE_CENTER_V1.coordinate_hash
    assert moved.cache_identity != PRAGUE_CENTER_V1.cache_identity


@pytest.mark.parametrize(
    "replacement",
    [
        {"key": "Praha"},
        {"version": 0},
        {"label": " "},
        {"latitude": 91.0},
        {"longitude": float("nan")},
        {"source": ""},
    ],
)
def test_reference_point_rejects_invalid_configuration(replacement: dict[str, object]) -> None:
    values: dict[str, object] = {
        "key": "valid_key",
        "version": 1,
        "label": "Valid",
        "latitude": 50.0,
        "longitude": 14.0,
        "source": "test",
    }
    values.update(replacement)

    with pytest.raises(ValueError):
        ReferencePoint(**values)  # type: ignore[arg-type]


def test_registry_is_immutable_and_unknown_key_fails_clearly() -> None:
    with pytest.raises(TypeError):
        REFERENCE_POINTS["other"] = PRAGUE_CENTER_V1  # type: ignore[index]
    with pytest.raises(ReferencePointNotFoundError, match="unknown reference point"):
        get_reference_point("missing")
