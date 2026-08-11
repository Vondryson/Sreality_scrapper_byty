"""Owner authorization seam, completed by Google OAuth wiring in M2-08."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from sreality_tracker.api.errors import ApiError


@dataclass(frozen=True, slots=True)
class OwnerIdentity:
    email: str
    subject: str
    csrf_token: str


def require_owner(request: Request) -> OwnerIdentity:
    manager = request.app.state.container.auth_manager
    identity: OwnerIdentity | None = (
        None
        if manager is None
        else manager.authenticate(request.cookies.get("sreality_session"))
    )
    if identity is None:
        raise ApiError(status_code=401, code="authentication_required", message="Sign-in required")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied_csrf = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(supplied_csrf, identity.csrf_token):
            raise ApiError(status_code=403, code="csrf_failed", message="CSRF validation failed")
    return identity


AuthenticatedOwner = Annotated[OwnerIdentity, Depends(require_owner)]
