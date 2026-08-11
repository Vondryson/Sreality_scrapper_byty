"""Command-line entry point for validation and manual scraper runs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from sqlalchemy import text

from sreality_tracker import __version__
from sreality_tracker.core.logging import configure_logging
from sreality_tracker.core.settings import ConfigurationError, Settings, load_settings
from sreality_tracker.db.models import ScrapeRunStatus, ScrapeRunTrigger
from sreality_tracker.db.session import create_database_engine, create_session_factory
from sreality_tracker.scraper.client import SrealityClient
from sreality_tracker.scraper.pipeline import RunResult, ScrapePipeline
from sreality_tracker.scraper.source import SrealityListingSource
from sreality_tracker.storage.raw import LocalRawStorage


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
        required=True,
        help="unique idempotency key, for example manual:2026-08-11T1200",
    )
    run_parser.add_argument(
        "--trigger",
        choices=[item.value for item in ScrapeRunTrigger],
        default=ScrapeRunTrigger.MANUAL.value,
    )
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
        result = _run_pipeline(
            settings,
            logical_key=str(args.logical_key),
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
            pipeline = ScrapePipeline(
                session_factory=create_session_factory(engine),
                source=SrealityListingSource(client),
                raw_storage=LocalRawStorage(Path.cwd() / settings.raw_storage_path),
                scraper_version=__version__,
            )
            return pipeline.execute(logical_key=logical_key, trigger=trigger)
    finally:
        engine.dispose()


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


def _write_json(payload: dict[str, object], *, stream: TextIO | None = None) -> None:
    output = sys.stdout if stream is None else stream
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), file=output)


if __name__ == "__main__":
    raise SystemExit(main())
