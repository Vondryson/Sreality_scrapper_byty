"""Signed owner sessions and Google OAuth authorization-code flow."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token

from sreality_tracker.api.errors import ApiError
from sreality_tracker.api.owner import OwnerIdentity

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SESSION_COOKIE = "sreality_session"
OAUTH_FLOW_COOKIE = "sreality_oauth_flow"
SESSION_MAX_AGE_SECONDS = 8 * 60 * 60
OAUTH_FLOW_MAX_AGE_SECONDS = 10 * 60


class AuthConfigurationError(RuntimeError):
    pass


class AuthTokenError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OAuthFlow:
    authorization_url: str
    cookie_value: str


@dataclass(frozen=True, slots=True)
class AuthManager:
    client_id: str
    client_secret: str
    redirect_uri: str
    owner_email: str
    codec: SessionCodec
    oauth_client: GoogleOAuthClient

    def begin_login(self) -> OAuthFlow:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = _base64url(hashlib.sha256(verifier.encode()).digest())
        cookie = self.codec.dumps(
            {
                "purpose": "oauth_flow",
                "state": state,
                "nonce": nonce,
                "verifier": verifier,
                "exp": int(time.time()) + OAUTH_FLOW_MAX_AGE_SECONDS,
            }
        )
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "prompt": "select_account",
            }
        )
        return OAuthFlow(
            authorization_url=f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}",
            cookie_value=cookie,
        )

    def complete_login(self, *, code: str, state: str, flow_cookie: str) -> tuple[str, str]:
        flow = self.codec.loads(flow_cookie, purpose="oauth_flow")
        expected_state = _required_string(flow, "state")
        if not hmac.compare_digest(state, expected_state):
            raise AuthTokenError("OAuth state mismatch")
        nonce = _required_string(flow, "nonce")
        verifier = _required_string(flow, "verifier")
        claims = self.oauth_client.exchange_code(
            code=code,
            redirect_uri=self.redirect_uri,
            client_id=self.client_id,
            client_secret=self.client_secret,
            code_verifier=verifier,
        )
        if claims.get("nonce") != nonce:
            raise AuthTokenError("OAuth nonce mismatch")
        email = claims.get("email")
        if not isinstance(email, str) or claims.get("email_verified") is not True:
            raise AuthTokenError("Google email is not verified")
        if not hmac.compare_digest(email.casefold(), self.owner_email.casefold()):
            raise ApiError(status_code=403, code="owner_not_allowed", message="Access denied")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthTokenError("Google subject is missing")
        csrf_token = secrets.token_urlsafe(32)
        session = self.codec.dumps(
            {
                "purpose": "owner_session",
                "sub": subject,
                "email": email,
                "csrf": csrf_token,
                "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS,
            }
        )
        return session, csrf_token

    def authenticate(self, cookie_value: str | None) -> OwnerIdentity | None:
        if cookie_value is None:
            return None
        try:
            payload = self.codec.loads(cookie_value, purpose="owner_session")
            email = _required_string(payload, "email")
            subject = _required_string(payload, "sub")
            csrf = _required_string(payload, "csrf")
        except AuthTokenError:
            return None
        if not hmac.compare_digest(email.casefold(), self.owner_email.casefold()):
            return None
        return OwnerIdentity(email=email, subject=subject, csrf_token=csrf)


class SessionCodec:
    def __init__(self, secret: str) -> None:
        if len(secret.encode()) < 32:
            raise AuthConfigurationError("session secret must contain at least 32 bytes")
        self._secret = secret.encode()

    def dumps(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        encoded = _base64url(raw)
        signature = _base64url(hmac.digest(self._secret, encoded.encode(), "sha256"))
        return f"{encoded}.{signature}"

    def loads(self, token: str, *, purpose: str) -> dict[str, Any]:
        try:
            encoded, supplied_signature = token.split(".", 1)
            expected_signature = _base64url(hmac.digest(self._secret, encoded.encode(), "sha256"))
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise AuthTokenError("session signature is invalid")
            payload = json.loads(_decode_base64url(encoded))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AuthTokenError("session token is malformed") from error
        if not isinstance(payload, dict) or payload.get("purpose") != purpose:
            raise AuthTokenError("session purpose is invalid")
        expires_at = payload.get("exp")
        if not isinstance(expires_at, int) or expires_at < int(time.time()):
            raise AuthTokenError("session token expired")
        return payload


class GoogleOAuthClient:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        verifier: Callable[[str, str], dict[str, Any]] | None = None,
    ) -> None:
        self._client = client or httpx.Client(timeout=20.0)
        self._owns_client = client is None
        self._verifier = verifier or _verify_google_id_token

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        try:
            response = self._client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise AuthTokenError("Google token exchange failed") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("id_token"), str):
            raise AuthTokenError("Google response does not contain an ID token")
        try:
            return self._verifier(payload["id_token"], client_id)
        except Exception as error:
            raise AuthTokenError("Google ID token verification failed") from error


def _verify_google_id_token(token: str, audience: str) -> dict[str, Any]:
    claims = google_id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
        token, GoogleAuthRequest(), audience
    )
    return dict(claims)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode_base64url(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode()


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AuthTokenError(f"session {key} is missing")
    return value
