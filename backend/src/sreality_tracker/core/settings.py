"""Validated application settings loaded exclusively from environment variables."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PRODUCTION = "production"


class ConfigurationError(RuntimeError):
    """Raised when application settings are missing or invalid."""


class Settings(BaseSettings):
    """Application configuration with secrets protected from repr and errors."""

    model_config = SettingsConfigDict(
        env_prefix="SREALITY_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Environment = Environment.LOCAL
    database_url: SecretStr
    raw_storage_path: Path = Path("data/raw")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    http_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    http_min_delay_seconds: float = Field(default=0.75, ge=0.5, le=60)
    http_max_attempts: int = Field(default=3, ge=1, le=6)
    http_backoff_base_seconds: float = Field(default=0.5, ge=0, le=30)
    http_jitter_max_seconds: float = Field(default=0.25, ge=0, le=10)
    routes_project_id: str | None = None
    routes_access_token: SecretStr | None = None
    routes_daily_request_limit: int = Field(default=300, ge=1, le=300)
    routes_max_attempts: int = Field(default=3, ge=1, le=6)
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: SecretStr | None = None
    google_oauth_redirect_uri: str = (
        "http://localhost:8000/api/v1/auth/google/callback"
    )
    owner_email: str | None = None
    session_secret: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        raw_url = value.get_secret_value()
        try:
            parsed = make_url(raw_url)
        except ArgumentError as error:
            raise ValueError("must be a valid SQLAlchemy database URL") from error
        if parsed.drivername != "postgresql+psycopg":
            raise ValueError("must use the postgresql+psycopg driver")
        if not parsed.username or not parsed.password or not parsed.database:
            raise ValueError("must include username, password, and database name")
        return value

    @field_validator("raw_storage_path")
    @classmethod
    def validate_relative_storage_path(cls, value: Path) -> Path:
        if value.is_absolute() or ".." in value.parts:
            raise ValueError("must be a relative path inside the project workspace")
        return value

    def database_url_value(self) -> str:
        """Return the database URL only at the adapter boundary."""
        return self.database_url.get_secret_value()

    def routes_access_token_value(self) -> str | None:
        """Return an optional short-lived token only at the provider boundary."""
        if self.routes_access_token is None:
            return None
        return self.routes_access_token.get_secret_value()

    @model_validator(mode="after")
    def validate_google_oauth(self) -> Settings:
        values_present = (
            self.google_oauth_client_id is not None,
            self.google_oauth_client_secret is not None,
            self.owner_email is not None,
            self.session_secret is not None,
        )
        if any(values_present) and not all(values_present):
            raise ValueError(
                "Google OAuth requires client ID, client secret, owner email, and session secret"
            )
        if not all(values_present):
            return self
        assert self.session_secret is not None
        if len(self.session_secret.get_secret_value().encode()) < 32:
            raise ValueError("session secret must contain at least 32 bytes")
        assert self.owner_email is not None
        if "@" not in self.owner_email or self.owner_email != self.owner_email.strip():
            raise ValueError("owner email must be a normalized email address")
        redirect = urlparse(self.google_oauth_redirect_uri)
        local_http = redirect.scheme == "http" and redirect.hostname == "localhost"
        if redirect.scheme != "https" and not local_http:
            raise ValueError("OAuth redirect URI must use HTTPS or HTTP localhost")
        return self


def load_settings() -> Settings:
    """Load settings and raise a concise error that never echoes input values."""
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as error:
        problems = []
        for item in error.errors(include_url=False, include_context=False, include_input=False):
            field = ".".join(str(part) for part in item["loc"])
            problems.append(f"{field}: {item['msg']}")
        raise ConfigurationError("Invalid configuration: " + "; ".join(problems)) from None
