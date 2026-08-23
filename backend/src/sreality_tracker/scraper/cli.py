"""Command-line entry point for validation and manual scraper runs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from sqlalchemy import text

from sreality_tracker import __version__
from sreality_tracker.core.logging import configure_logging
from sreality_tracker.core.settings import (
    ConfigurationError,
    Settings,
    StorageBackend,
    load_settings,
)
from sreality_tracker.db.models import ScrapeRunStatus, ScrapeRunTrigger
from sreality_tracker.db.session import create_database_engine, create_session_factory
from sreality_tracker.distances.road import BackfillResult, RoadDistanceEnricher
from sreality_tracker.distances.routes import RoutesClient
from sreality_tracker.scraper.client import SrealityClient
from sreality_tracker.scraper.pipeline import RunResult, ScrapePipeline
from sreality_tracker.scraper.source import SrealityListingSource
from sreality_tracker.storage.raw import GcsRawStorage, LocalRawStorage, RawStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sreality-scrape")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "check",
        help="validate configuration and database connectivity without writes or HTTP requests",
    )
    run_parser = subparsers.add_parser(
        "run", help="run both listing categories and persist results"
    )
    run_parser.add_argument(
        "--logical-key",
        help="unique idempotency key; defaults to <trigger>:<current UTC timestamp>",
    )
    run_parser.add_argument(
        "--trigger",
        choices=[item.value for item in ScrapeRunTrigger],
        default=ScrapeRunTrigger.MANUAL.value,
    )
    backfill_parser = subparsers.add_parser(
        "routes-backfill",
        help="fill missing road distances with the configured bounded Routes quota",
    )
    backfill_parser.add_argument("--limit", type=int, default=300, choices=range(1, 301))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        configure_logging(level=settings.log_level)
        if args.command == "check":
            _check_database(settings)
            _write_json({"status": "ready", "mode": "read_only"})
            return 0
        if args.command == "routes-backfill":
            backfill = _run_routes_backfill(settings, limit=int(args.limit))
            _write_json(_backfill_payload(backfill))
            return 0 if backfill.failed == 0 else 1
        result = _run_pipeline(
            settings,
            logical_key=(
                str(args.logical_key)
                if args.logical_key is not None
                else _generated_logical_key(ScrapeRunTrigger(str(args.trigger)))
            ),
            trigger=ScrapeRunTrigger(str(args.trigger)),
        )
        _write_json(_result_payload(result))
        return 0 if result.status is ScrapeRunStatus.SUCCEEDED else 1
    except ConfigurationError:
        _write_json({"status": "error", "error_type": "ConfigurationError"}, stream=sys.stderr)
        return 2
    except Exception as error:
        _write_json(
            {"status": "error", "error_type": type(error).__name__},
            stream=sys.stderr,
        )
        return 1


def _check_database(settings: Settings) -> None:
    engine = create_database_engine(settings.database_url_value())
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()


def _generated_logical_key(trigger: ScrapeRunTrigger) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{trigger.value}:{timestamp}"


def _run_pipeline(settings: Settings, *, logical_key: str, trigger: ScrapeRunTrigger) -> RunResult:
    engine = create_database_engine(settings.database_url_value())
    try:
        with SrealityClient(
            timeout_seconds=settings.http_timeout_seconds,
            min_delay_seconds=settings.http_min_delay_seconds,
            max_attempts=settings.http_max_attempts,
            backoff_base_seconds=settings.http_backoff_base_seconds,
            jitter_max_seconds=settings.http_jitter_max_seconds,
        ) as client:
            session_factory = create_session_factory(engine)
            routes_client = _routes_client(settings)
            pipeline = ScrapePipeline(
                session_factory=session_factory,
                source=SrealityListingSource(client),
                raw_storage=_raw_storage(settings),
                scraper_version=__version__,
                road_distance_enricher=(
                    None
                    if routes_client is None
                    else RoadDistanceEnricher(
                        session_factory=session_factory,
                        client=routes_client,
                    )
                ),
            )
            try:
                return pipeline.execute(logical_key=logical_key, trigger=trigger)
            finally:
                if routes_client is not None:
                    routes_client.close()
    finally:
        engine.dispose()


def _raw_storage(settings: Settings) -> RawStorage:
    if settings.storage_backend is StorageBackend.GCS:
        assert settings.storage_bucket is not None
        return GcsRawStorage.from_bucket_name(
            settings.storage_bucket,
            project=settings.gcp_project_id,
        )
    return LocalRawStorage(Path.cwd() / settings.raw_storage_path)


def _result_payload(result: RunResult) -> dict[str, object]:
    return {
        "status": result.status.value,
        "run_id": str(result.run_id),
        "logical_key": result.logical_key,
        "found_count": result.found_count,
        "new_count": result.new_count,
        "changed_count": result.changed_count,
        "error_count": result.error_count,
        "deactivated_count": result.deactivated_count,
        "chata_complete": result.chata_complete,
        "chalupa_complete": result.chalupa_complete,
    }


def _run_routes_backfill(settings: Settings, *, limit: int) -> BackfillResult:
    client = _routes_client(settings, required=True)
    assert client is not None
    engine = create_database_engine(settings.database_url_value())
    try:
        return RoadDistanceEnricher(
            session_factory=create_session_factory(engine),
            client=client,
        ).backfill(limit=min(limit, settings.routes_daily_request_limit))
    finally:
        client.close()
        engine.dispose()


def _routes_client(settings: Settings, *, required: bool = False) -> RoutesClient | None:
    token = settings.routes_access_token_value()
    project_id = settings.routes_project_id
    if token is None or project_id is None:
        if required:
            raise ConfigurationError(
                "Routes backfill requires routes_project_id and a short-lived routes_access_token"
            )
        return None
    return RoutesClient(
        project_id=project_id,
        access_token_provider=lambda: token,
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.routes_max_attempts,
        request_limit=settings.routes_daily_request_limit,
        backoff_base_seconds=settings.http_backoff_base_seconds,
        jitter_max_seconds=settings.http_jitter_max_seconds,
    )


def _backfill_payload(result: BackfillResult) -> dict[str, object]:
    return {
        "status": "succeeded" if result.failed == 0 else "partial",
        "considered": result.considered,
        "created": result.created,
        "cache_hits": result.cache_hits,
        "failed": result.failed,
        "provider_requests": result.provider_requests,
    }


def _write_json(payload: dict[str, object], *, stream: TextIO | None = None) -> None:
    output = sys.stdout if stream is None else stream
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=output)


if __name__ == "__main__":
    raise SystemExit(main())
