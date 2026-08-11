from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from sreality_tracker.core.settings import ConfigurationError
from sreality_tracker.scraper import cli


def test_check_mode_is_read_only_and_returns_machine_readable_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = SimpleNamespace(log_level="INFO")
    calls: list[object] = []
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "_check_database", calls.append)

    exit_code = cli.main(["check"])

    assert exit_code == 0
    assert calls == [settings]
    assert json.loads(capsys.readouterr().out) == {"status": "ready", "mode": "read_only"}


def test_configuration_error_does_not_echo_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_settings() -> None:
        raise ConfigurationError("password=super-secret")

    monkeypatch.setattr(cli, "load_settings", fail_settings)

    assert cli.main(["check"]) == 2
    output = capsys.readouterr().err
    assert "super-secret" not in output
    assert json.loads(output)["error_type"] == "ConfigurationError"


def test_routes_backfill_returns_usage_metric(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = SimpleNamespace(log_level="INFO")
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(
        cli,
        "_run_routes_backfill",
        lambda _settings, *, limit: cli.BackfillResult(
            considered=limit,
            created=2,
            cache_hits=1,
            failed=0,
            provider_requests=2,
        ),
    )

    assert cli.main(["routes-backfill", "--limit", "3"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "succeeded",
        "considered": 3,
        "created": 2,
        "cache_hits": 1,
        "failed": 0,
        "provider_requests": 2,
    }
