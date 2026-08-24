"""Structured JSON logging with bounded context and secret redaction."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any, TextIO

LOGGER_NAME = "sreality_tracker"
CONTEXT_FIELDS = (
    "event",
    "step",
    "run_id",
    "listing_id",
    "error_type",
    "status",
    "trigger",
    "kind",
)
METRIC_FIELDS = (
    "duration_seconds",
    "found_count",
    "new_count",
    "changed_count",
    "error_count",
    "deactivated_count",
    "provider_requests",
)
REDACTED = "[REDACTED]"
_URL_PASSWORD = re.compile(r"(?P<prefix>://[^:/\s]+:)[^@\s]+@")
_KEY_VALUE_SECRET = re.compile(
    r"(?i)(?P<key>password|token|secret|api[_-]?key|authorization|cookie)"
    r"(?P<separator>\s*[=:]\s*)(?P<value>[^\s,;]+)"
)


def redact_secrets(value: str) -> str:
    """Remove common credentials from a rendered log message."""
    value = _URL_PASSWORD.sub(rf"\g<prefix>{REDACTED}@", value)
    return _KEY_VALUE_SECRET.sub(
        lambda match: f"{match.group('key')}{match.group('separator')}{REDACTED}",
        value,
    )


class JsonFormatter(logging.Formatter):
    """Render one compact JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
        }
        for field in CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = str(value)
        for field in METRIC_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                payload[field] = value
        if record.exc_info is not None and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(*, level: str, stream: TextIO | None = None) -> logging.Logger:
    """Configure and return the isolated application logger."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def bind_context(
    logger: logging.Logger,
    *,
    event: str | None = None,
    step: str | None = None,
    run_id: str | None = None,
    listing_id: str | int | None = None,
) -> logging.LoggerAdapter[logging.Logger]:
    """Bind the supported operational context to subsequent log records."""
    extra = {
        key: value
        for key, value in {
            "event": event,
            "step": step,
            "run_id": run_id,
            "listing_id": listing_id,
        }.items()
        if value is not None
    }
    return logging.LoggerAdapter(logger, extra)
