from __future__ import annotations

import asyncio
import time
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from sreality_tracker.api.app import create_app
from sreality_tracker.api.dependencies import get_session
from sreality_tracker.core.settings import Environment, Settings


def build_test_settings() -> Settings:
    return Settings(
        database_url=SecretStr("postgresql+psycopg://test:test@localhost/test"),
        environment=Environment.TEST,
        google_oauth_client_id="test-client.apps.googleusercontent.com",
        google_oauth_client_secret=SecretStr("oauth-secret"),
        owner_email="owner@example.com",
        session_secret=SecretStr("s" * 32),
    )


async def request_many(
    app: FastAPI, *paths: str, headers: dict[str, str] | None = None
) -> list[httpx.Response]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return [await client.get(path, headers=headers) for path in paths]


async def patch_json(
    app: FastAPI,
    path: str,
    payload: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.patch(path, json=payload, headers=headers)


def owner_headers(app: FastAPI, *, csrf: bool = True) -> dict[str, str]:
    manager = app.state.container.auth_manager
    assert manager is not None
    csrf_token = "test-csrf-token"
    cookie = manager.codec.dumps(
        {
            "purpose": "owner_session",
            "sub": "owner-subject",
            "email": "owner@example.com",
            "csrf": csrf_token,
            "exp": int(time.time()) + 300,
        }
    )
    headers = {"Cookie": f"sreality_session={cookie}"}
    if csrf:
        headers["X-CSRF-Token"] = csrf_token
    return headers


def test_versioned_health_readiness_and_openapi_contract() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app = create_app(settings=build_test_settings(), engine=engine)
    live, ready, openapi = asyncio.run(
        request_many(
            app,
            "/api/v1/health/live",
            "/api/v1/health/ready",
            "/openapi.json",
        )
    )
    assert live.json() == {"status": "alive"}
    assert ready.json() == {"status": "ready"}
    schema = openapi.json()

    assert schema["info"]["title"] == "Sreality Chaty Tracker API"
    assert schema["info"]["version"] == "0.1.0"
    assert "/api/v1/health/live" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]
    assert "/api/v1/listings" in schema["paths"]
    assert "/api/v1/listings/{listing_id}" in schema["paths"]
    assert "/api/v1/listings/{listing_id}/history" in schema["paths"]
    assert "/api/v1/map/listings" in schema["paths"]
    assert "/api/v1/analytics/price-medians" in schema["paths"]
    assert "/api/v1/listings/{listing_id}/user-data" in schema["paths"]
    assert "/api/v1/auth/google/login" in schema["paths"]
    assert "/api/v1/auth/google/callback" in schema["paths"]
    assert "/api/v1/auth/session" in schema["paths"]
    assert "/api/v1/auth/logout" in schema["paths"]
    assert "/api/v1/operations/scrape-runs/latest" in schema["paths"]
    assert "/api/v1/operations/scrape-runs" in schema["paths"]
    engine.dispose()


def test_listing_range_validation_uses_uniform_error_contract() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    app = create_app(settings=build_test_settings(), engine=engine)

    [response] = asyncio.run(
        request_many(
            app,
            "/api/v1/listings?price_min=200&price_max=100",
            headers=owner_headers(app),
        )
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "validation_error", "message": "Request validation failed"}
    }
    engine.dispose()


def test_readiness_and_not_found_use_uniform_safe_errors() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    app = create_app(settings=build_test_settings(), engine=engine, readiness_probe=lambda: False)
    readiness, missing = asyncio.run(request_many(app, "/api/v1/health/ready", "/api/v1/missing"))

    assert readiness.status_code == 503
    assert readiness.json() == {
        "error": {"code": "database_unavailable", "message": "Service is not ready"}
    }
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "http_404", "message": "Resource not found"}}
    engine.dispose()


def test_request_scoped_database_session_is_injected() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app = create_app(settings=build_test_settings(), engine=engine)

    @app.get("/api/v1/test-session", include_in_schema=False)
    def session_endpoint(session: Annotated[Session, Depends(get_session)]) -> dict[str, bool]:
        return {"injected": session.is_active}

    [response] = asyncio.run(request_many(app, "/api/v1/test-session"))

    assert response.status_code == 200
    assert response.json() == {"injected": True}
    engine.dispose()


def test_private_listing_write_requires_owner_identity() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    app = create_app(settings=build_test_settings(), engine=engine)

    response = asyncio.run(
        patch_json(app, "/api/v1/listings/1/user-data", {"is_favorite": True})
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "authentication_required", "message": "Sign-in required"}
    }
    engine.dispose()


def test_owner_session_and_csrf_are_enforced() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    app = create_app(settings=build_test_settings(), engine=engine)
    [denied] = asyncio.run(request_many(app, "/api/v1/listings"))
    [valid] = asyncio.run(
        request_many(
            app,
            "/api/v1/auth/session",
            headers=owner_headers(app),
        )
    )
    assert denied.status_code == 401
    assert valid.status_code == 200
    assert valid.json()["email"] == "owner@example.com"

    async def logout(headers: dict[str, str]) -> httpx.Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
            return await client.post("/api/v1/auth/logout", headers=headers)

    csrf_failure = asyncio.run(logout(owner_headers(app, csrf=False)))
    success = asyncio.run(logout(owner_headers(app)))
    assert csrf_failure.status_code == 403
    assert csrf_failure.json()["error"]["code"] == "csrf_failed"
    assert success.status_code == 200
    assert success.json() == {"authenticated": False}
    engine.dispose()
