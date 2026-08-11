from __future__ import annotations

from pathlib import Path

import pytest

from sreality_tracker.core.settings import ConfigurationError, Environment, load_settings

DATABASE_URL = "postgresql+psycopg://sreality:sreality_local_only@localhost:5432/sreality_tracker"


def test_settings_load_valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SREALITY_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("SREALITY_ENVIRONMENT", "test")
    monkeypatch.setenv("SREALITY_RAW_STORAGE_PATH", "data/test-raw")
    monkeypatch.setenv("SREALITY_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SREALITY_ROUTES_PROJECT_ID", "sreality-scrapper-504307")
    monkeypatch.setenv("SREALITY_ROUTES_ACCESS_TOKEN", "short-lived-secret-token")

    settings = load_settings()

    assert settings.environment is Environment.TEST
    assert settings.database_url_value() == DATABASE_URL
    assert settings.raw_storage_path == Path("data/test-raw")
    assert settings.log_level == "WARNING"
    assert settings.routes_project_id == "sreality-scrapper-504307"
    assert settings.routes_access_token_value() == "short-lived-secret-token"
    assert "sreality_local_only" not in repr(settings)
    assert "short-lived-secret-token" not in repr(settings)


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
        ("SREALITY_RAW_STORAGE_PATH", "../outside", "relative path"),
        ("SREALITY_ROUTES_DAILY_REQUEST_LIMIT", "301", "less than or equal to 300"),
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
