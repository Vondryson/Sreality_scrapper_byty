"""Deterministic local great-circle distance calculations."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

EARTH_MEAN_RADIUS_KM = 6371.0088
COORDINATE_PRECISION = 7


@dataclass(frozen=True, slots=True)
class Coordinates:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be finite and between -90 and 90")
        if not math.isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be finite and between -180 and 180")

    @property
    def coordinate_hash(self) -> str:
        normalized = (
            f"{self.latitude:.{COORDINATE_PRECISION}f},{self.longitude:.{COORDINATE_PRECISION}f}"
        )
        return hashlib.sha256(normalized.encode("ascii")).hexdigest()


def optional_coordinates(latitude: float | None, longitude: float | None) -> Coordinates | None:
    """Return validated paired coordinates or None for missing/invalid source GPS."""
    if latitude is None or longitude is None:
        return None
    try:
        return Coordinates(latitude=latitude, longitude=longitude)
    except ValueError:
        return None


def haversine_distance_km(origin: Coordinates, target: Coordinates) -> float:
    """Calculate the shortest surface distance on the IUGG mean-radius sphere."""
    origin_latitude = math.radians(origin.latitude)
    target_latitude = math.radians(target.latitude)
    latitude_delta = target_latitude - origin_latitude
    longitude_delta = math.radians(target.longitude - origin.longitude)
    haversine = math.sin(latitude_delta / 2) ** 2 + (
        math.cos(origin_latitude) * math.cos(target_latitude) * math.sin(longitude_delta / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(haversine), math.sqrt(max(0.0, 1 - haversine)))
    return EARTH_MEAN_RADIUS_KM * central_angle
