"""Short-lived Google ADC tokens for server-side Routes requests."""

from __future__ import annotations

import google.auth
from google.auth.credentials import Credentials
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request

from sreality_tracker.distances.routes import RoutesError

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class GoogleAdcAccessTokenProvider:
    """Refresh and return an ADC token without persisting or logging it."""

    def __init__(
        self,
        project_id: str,
        *,
        credentials: Credentials | None = None,
        request: Request | None = None,
    ) -> None:
        if not project_id.strip():
            raise ValueError("project_id must not be empty")
        if credentials is None:
            try:
                credentials, _ = google.auth.default(
                    scopes=[CLOUD_PLATFORM_SCOPE],
                    quota_project_id=project_id,
                )
            except GoogleAuthError as error:
                raise RoutesError("Google ADC credentials are unavailable") from error
        self._credentials = credentials
        self._request = request or Request()

    def __call__(self) -> str:
        try:
            if not self._credentials.valid:
                # google-auth does not currently expose a typed ``refresh`` method.
                self._credentials.refresh(self._request)  # type: ignore[no-untyped-call]
        except GoogleAuthError as error:
            raise RoutesError("Google ADC access token refresh failed") from error
        token = self._credentials.token
        if not isinstance(token, str) or not token.strip():
            raise RoutesError("Google ADC access token is unavailable")
        return token
