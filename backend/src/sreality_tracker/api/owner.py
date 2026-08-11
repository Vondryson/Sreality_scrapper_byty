"""Owner authorization seam, completed by Google OAuth wiring in M2-08."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from sreality_tracker.api.errors import ApiError


@dataclass(frozen=True, slots=True)
class OwnerIdentity:
    email: str


def require_owner(request: Request) -> OwnerIdentity:
    identity = getattr(request.state, "owner_identity", None)
    if not isinstance(identity, OwnerIdentity):
        raise ApiError(status_code=401, code="authentication_required", message="Sign-in required")
    return identity


AuthenticatedOwner = Annotated[OwnerIdentity, Depends(require_owner)]
