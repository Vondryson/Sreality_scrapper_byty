from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from sreality_tracker.core.settings import ConfigurationError, StorageBackend
from sreality_tracker.db.models import ScrapeRunStatus, ScrapeRunTrigger
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


def test_run_generates_unique_scheduled_logical_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = SimpleNamespace(log_level="INFO")
    captured: dict[str, object] = {}
    result = SimpleNamespace(
        status=ScrapeRunStatus.SUCCEEDED,
        run_id="run-id",
        logical_key="scheduled:generated",
        found_count=0,
        new_count=0,
        changed_count=0,
        error_count=0,
        deactivated_count=0,
        chata_complete=True,
        chalupa_complete=True,
    )
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(
        cli,
        "_generated_logical_key",
        lambda trigger: f"{trigger.value}:generated",
    )

    def run_pipeline(_settings: object, *, logical_key: str, trigger: ScrapeRunTrigger) -> object:
        captured.update(logical_key=logical_key, trigger=trigger)
        return result

    monkeypatch.setattr(cli, "_run_pipeline", run_pipeline)

    assert cli.main(["run", "--trigger", "scheduled"]) == 0
    assert captured == {
        "logical_key": "scheduled:generated",
        "trigger": ScrapeRunTrigger.SCHEDULED,
    }
    assert json.loads(capsys.readouterr().out)["logical_key"] == "scheduled:generated"


def test_raw_storage_selects_validated_gcs_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = object()
    settings = SimpleNamespace(
        storage_backend=StorageBackend.GCS,
        storage_bucket="sreality-scrapper-504307-application-data",
        gcp_project_id="sreality-scrapper-504307",
    )
    calls: list[tuple[str, str | None]] = []

    def from_bucket_name(bucket_name: str, *, project: str | None = None) -> object:
        calls.append((bucket_name, project))
        return expected

    monkeypatch.setattr(cli.GcsRawStorage, "from_bucket_name", from_bucket_name)

    assert cli._raw_storage(settings) is expected
    assert calls == [("sreality-scrapper-504307-application-data", "sreality-scrapper-504307")]
