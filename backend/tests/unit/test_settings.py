from __future__ import annotations

from pathlib import Path

import pytest

from sreality_tracker.core.settings import (
    ConfigurationError,
    Environment,
    StorageBackend,
    load_settings,
)

DATABASE_URL = "postgresql+psycopg://sreality:sreality_local_only@localhost:5432/sreality_tracker"


def test_settings_load_valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SREALITY_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("SREALITY_ENVIRONMENT", "test")
    monkeypatch.setenv("SREALITY_RAW_STORAGE_PATH", "data/test-raw")
    monkeypatch.setenv("SREALITY_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SREALITY_ROUTES_PROJECT_ID", "sreality-scrapper-504307")
    monkeypatch.setenv("SREALITY_ROUTES_ACCESS_TOKEN", "short-lived-secret-token")
    monkeypatch.setenv("SREALITY_GOOGLE_OAUTH_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setenv("SREALITY_GOOGLE_OAUTH_CLIENT_SECRET", "oauth-client-secret")
    monkeypatch.setenv("SREALITY_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("SREALITY_SESSION_SECRET", "session-signing-secret-that-is-long-enough")

    settings = load_settings()

    assert settings.environment is Environment.TEST
    assert settings.storage_backend is StorageBackend.LOCAL
    assert settings.database_url_value() == DATABASE_URL
    assert settings.raw_storage_path == Path("data/test-raw")
    assert settings.log_level == "WARNING"
    assert settings.routes_project_id == "sreality-scrapper-504307"
    assert settings.routes_access_token_value() == "short-lived-secret-token"
    assert settings.google_oauth_client_id == "test-client.apps.googleusercontent.com"
    assert settings.owner_email == "owner@example.com"
    assert "sreality_local_only" not in repr(settings)
    assert "short-lived-secret-token" not in repr(settings)
    assert "oauth-client-secret" not in repr(settings)
    assert "session-signing-secret-that-is-long-enough" not in repr(settings)


def test_missing_database_url_fails_without_echoing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SREALITY_DATABASE_URL", raising=False)

    with pytest.raises(ConfigurationError) as captured:
        load_settings()

    assert "database_url" in str(captured.value)


@pytest.mark.parametrize(
    ("variable", "value", "expected"),
    [
        ("SREALITY_DATABASE_URL", "sqlite:///secret-value.db", "postgresql+psycopg"),
        ("SREALITY_RAW_STORAGE_PATH", "C:/private/data", "relative path"),
        ("SREALITY_RAW_STORAGE_PATH", r"\\server\share\data", "relative path"),
        ("SREALITY_RAW_STORAGE_PATH", "../outside", "relative path"),
        ("SREALITY_RAW_STORAGE_PATH", r"..\outside", "relative path"),
        ("SREALITY_ROUTES_DAILY_REQUEST_LIMIT", "301", "less than or equal to 300"),
        ("SREALITY_FRONTEND_URL", "http://attacker.example/path", "HTTPS or HTTP localhost"),
    ],
)
def test_invalid_configuration_is_clear_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
    value: str,
    expected: str,
) -> None:
    monkeypatch.setenv("SREALITY_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv(variable, value)

    with pytest.raises(ConfigurationError) as captured:
        load_settings()

    message = str(captured.value)
    assert expected in message
    assert value not in message


def test_partial_oauth_configuration_and_short_session_secret_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SREALITY_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("SREALITY_GOOGLE_OAUTH_CLIENT_ID", "client.apps.googleusercontent.com")
    with pytest.raises(ConfigurationError, match="Google OAuth requires"):
        load_settings()

    monkeypatch.setenv("SREALITY_GOOGLE_OAUTH_CLIENT_SECRET", "oauth-secret")
    monkeypatch.setenv("SREALITY_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("SREALITY_SESSION_SECRET", "too-short")
    with pytest.raises(ConfigurationError, match="at least 32 bytes"):
        load_settings()


def test_gcs_storage_requires_exact_approved_project_and_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SREALITY_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("SREALITY_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("SREALITY_GCP_PROJECT_ID", "wrong-project")
    monkeypatch.setenv("SREALITY_STORAGE_BUCKET", "wrong-bucket")

    with pytest.raises(ConfigurationError, match="approved GCP project"):
        load_settings()

    monkeypatch.setenv("SREALITY_GCP_PROJECT_ID", "sreality-scrapper-504307")
    with pytest.raises(ConfigurationError, match="approved private application bucket"):
        load_settings()

    monkeypatch.setenv("SREALITY_STORAGE_BUCKET", "sreality-scrapper-504307-application-data")
    settings = load_settings()

    assert settings.storage_backend is StorageBackend.GCS
    assert settings.gcp_project_id == "sreality-scrapper-504307"


def test_cloud_run_trigger_requires_complete_managed_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SREALITY_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("SREALITY_CLOUD_RUN_REGION", "europe-west1")
    with pytest.raises(ConfigurationError, match="region and scraper job name"):
        load_settings()

    monkeypatch.setenv("SREALITY_SCRAPER_JOB_NAME", "untrusted-job")
    with pytest.raises(ConfigurationError, match="managed scraper job"):
        load_settings()

    monkeypatch.setenv("SREALITY_SCRAPER_JOB_NAME", "sreality-tracker-scraper")
    settings = load_settings()

    assert settings.cloud_run_region == "europe-west1"
    assert settings.scraper_job_name == "sreality-tracker-scraper"
