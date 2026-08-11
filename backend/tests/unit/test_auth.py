import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from sreality_tracker.api.auth import (
    AuthManager,
    AuthTokenError,
    GoogleOAuthClient,
    OAuthFlow,
    SessionCodec,
)
from sreality_tracker.api.errors import ApiError


def build_manager(*, email: str = "owner@example.com") -> tuple[AuthManager, OAuthFlow]:
    claims: dict[str, object] = {}
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"id_token": "signed-id-token"})
    )
    http_client = httpx.Client(transport=transport)
    oauth_client = GoogleOAuthClient(
        client=http_client,
        verifier=lambda _token, _audience: dict(claims),
    )
    manager = AuthManager(
        client_id="test-client.apps.googleusercontent.com",
        client_secret="client-secret",
        redirect_uri="http://localhost:8000/api/v1/auth/google/callback",
        owner_email="owner@example.com",
        codec=SessionCodec("s" * 32),
        oauth_client=oauth_client,
    )
    flow = manager.begin_login()
    flow_payload = manager.codec.loads(flow.cookie_value, purpose="oauth_flow")
    claims.update(
        {
            "sub": "google-subject",
            "email": email,
            "email_verified": True,
            "nonce": flow_payload["nonce"],
        }
    )
    return manager, flow


def test_oauth_flow_uses_pkce_nonce_allowlist_and_signed_session() -> None:
    manager, flow = build_manager()
    query = parse_qs(urlparse(flow.authorization_url).query)
    assert query["scope"] == ["openid email profile"]
    assert query["code_challenge_method"] == ["S256"]
    assert "nonce" in query

    session_cookie, csrf = manager.complete_login(
        code="authorization-code",
        state=query["state"][0],
        flow_cookie=flow.cookie_value,
    )
    identity = manager.authenticate(session_cookie)
    assert identity is not None
    assert identity.email == "owner@example.com"
    assert identity.subject == "google-subject"
    assert identity.csrf_token == csrf


def test_non_allowlisted_google_account_is_denied() -> None:
    manager, flow = build_manager(email="intruder@example.com")
    state = parse_qs(urlparse(flow.authorization_url).query)["state"][0]
    with pytest.raises(ApiError) as captured:
        manager.complete_login(code="code", state=state, flow_cookie=flow.cookie_value)
    assert captured.value.status_code == 403
    assert captured.value.code == "owner_not_allowed"


def test_session_rejects_tampering_expiry_and_wrong_purpose() -> None:
    codec = SessionCodec("s" * 32)
    valid = codec.dumps(
        {"purpose": "owner_session", "exp": int(time.time()) + 60, "email": "x"}
    )
    with pytest.raises(AuthTokenError):
        codec.loads(valid + "tampered", purpose="owner_session")
    expired = codec.dumps({"purpose": "owner_session", "exp": int(time.time()) - 1})
    with pytest.raises(AuthTokenError, match="expired"):
        codec.loads(expired, purpose="owner_session")
    with pytest.raises(AuthTokenError, match="purpose"):
        codec.loads(valid, purpose="oauth_flow")
