from __future__ import annotations

import json
from io import StringIO

from sreality_tracker.core.logging import bind_context, configure_logging


def test_json_log_contains_operational_context() -> None:
    stream = StringIO()
    logger = configure_logging(level="INFO", stream=stream)
    contextual = bind_context(
        logger,
        event="listing_observed",
        step="parse_detail",
        run_id="run-123",
        listing_id=456,
    )

    contextual.info("Detail parsed")

    payload = json.loads(stream.getvalue())
    assert payload["level"] == "INFO"
    assert payload["logger"] == "sreality_tracker"
    assert payload["message"] == "Detail parsed"
    assert payload["event"] == "listing_observed"
    assert payload["step"] == "parse_detail"
    assert payload["run_id"] == "run-123"
    assert payload["listing_id"] == "456"


def test_json_log_preserves_allowlisted_numeric_metrics() -> None:
    stream = StringIO()
    logger = configure_logging(level="INFO", stream=stream)

    logger.info(
        "Category completed",
        extra={
            "event": "category_scrape_completed",
            "kind": "chata",
            "found_count": 2401,
            "duration_seconds": 12.345,
        },
    )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "category_scrape_completed"
    assert payload["kind"] == "chata"
    assert payload["found_count"] == 2401
    assert payload["duration_seconds"] == 12.345


def test_log_message_and_exception_redact_secrets() -> None:
    stream = StringIO()
    logger = configure_logging(level="ERROR", stream=stream)

    try:
        raise RuntimeError("password=exception-secret")
    except RuntimeError:
        logger.exception(
            "Request failed token=token-secret "
            "url=postgresql+psycopg://user:database-secret@localhost/database"
        )

    output = stream.getvalue()
    payload = json.loads(output)
    assert "token-secret" not in output
    assert "database-secret" not in output
    assert "exception-secret" not in output
    assert payload["exception_type"] == "RuntimeError"
    assert "[REDACTED]" in payload["message"]
