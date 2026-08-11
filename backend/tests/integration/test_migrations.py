from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

EXPECTED_TABLES = {
    "alembic_version",
    "scrape_runs",
    "listings",
    "listing_observations",
    "listing_events",
    "listing_images",
    "listing_distances",
    "user_listing_data",
}
EXPECTED_ENUMS = {
    "listing_kind",
    "scrape_run_trigger",
    "scrape_run_status",
    "listing_event_type",
    "image_archive_status",
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def migration_config(database_url: str) -> Config:
    config = Config(REPOSITORY_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["database_url"] = database_url
    config.attributes["expected_database"] = "sreality_tracker_test"
    return config


def current_tables(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def current_application_enums(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT typname FROM pg_type WHERE typname = ANY(CAST(:names AS text[]))"),
                {"names": sorted(EXPECTED_ENUMS)},
            )
            return {str(row.typname) for row in rows}
    finally:
        engine.dispose()


@pytest.mark.integration
def test_initial_migration_upgrade_downgrade_upgrade() -> None:
    database_url = os.getenv("SREALITY_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("SREALITY_TEST_DATABASE_URL is not configured")

    parsed_url = make_url(database_url)
    assert parsed_url.drivername == "postgresql+psycopg"
    assert parsed_url.database == "sreality_tracker_test", (
        "Migration integration tests are destructive and require "
        "the disposable sreality_tracker_test database"
    )

    config = migration_config(database_url)
    command.upgrade(config, "head")
    assert current_tables(database_url) == EXPECTED_TABLES
    assert current_application_enums(database_url) == EXPECTED_ENUMS

    command.downgrade(config, "base")
    assert current_tables(database_url) == {"alembic_version"}
    assert current_application_enums(database_url) == set()

    command.upgrade(config, "head")
    assert current_tables(database_url) == EXPECTED_TABLES
    command.check(config)
