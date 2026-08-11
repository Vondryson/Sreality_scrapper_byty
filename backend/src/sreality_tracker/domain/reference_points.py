"""Versioned geographic reference points used by all distance calculations."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

REFERENCE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
COORDINATE_PRECISION = 7


class ReferencePointNotFoundError(LookupError):
    """Raised when a reference-point key is not registered."""


@dataclass(frozen=True, slots=True)
class ReferencePoint:
    """Stable WGS84 origin whose version participates in distance cache keys."""

    key: str
    version: int
    label: str
    latitude: float
    longitude: float
    source: str

    def __post_init__(self) -> None:
        if REFERENCE_KEY_PATTERN.fullmatch(self.key) is None:
            raise ValueError("reference key must be a lowercase stable identifier")
        if isinstance(self.version, bool) or self.version <= 0:
            raise ValueError("reference version must be a positive integer")
        if not self.label.strip():
            raise ValueError("reference label must not be empty")
        if not self.source.strip():
            raise ValueError("reference source must not be empty")
        if not math.isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError("reference latitude must be finite and between -90 and 90")
        if not math.isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError("reference longitude must be finite and between -180 and 180")

    @property
    def coordinate_hash(self) -> str:
        """Return a deterministic hash of normalized WGS84 coordinates."""
        normalized = (
            f"{self.latitude:.{COORDINATE_PRECISION}f},{self.longitude:.{COORDINATE_PRECISION}f}"
        )
        return hashlib.sha256(normalized.encode("ascii")).hexdigest()

    @property
    def cache_identity(self) -> tuple[str, int, str]:
        return self.key, self.version, self.coordinate_hash


PRAGUE_CENTER_V1: Final = ReferencePoint(
    key="praha_marianske_namesti",
    version=1,
    label="Praha - Mariánské náměstí",
    latitude=50.0871072,
    longitude=14.4178281,
    source="RÚIAN address place 21714746; Mariánské náměstí 2/2, Praha 1",
)
DEFAULT_REFERENCE_POINT_KEY: Final = PRAGUE_CENTER_V1.key
REFERENCE_POINTS = MappingProxyType({PRAGUE_CENTER_V1.key: PRAGUE_CENTER_V1})


def get_reference_point(key: str = DEFAULT_REFERENCE_POINT_KEY) -> ReferencePoint:
    """Resolve a reference point from the immutable central registry."""
    try:
        return REFERENCE_POINTS[key]
    except KeyError:
        raise ReferencePointNotFoundError(f"unknown reference point: {key}") from None
