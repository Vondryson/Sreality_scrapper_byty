from typing import cast

from sqlalchemy import Table, UniqueConstraint

from sreality_tracker.db.base import Base
from sreality_tracker.db.models import Listing, ListingObservation, ScrapeRun
from sreality_tracker.db.session import create_database_engine


def test_metadata_contains_all_m1_tables() -> None:
    assert set(Base.metadata.tables) == {
        "scrape_runs",
        "listings",
        "listing_observations",
        "listing_events",
        "listing_images",
        "listing_distances",
        "user_listing_data",
    }


def test_external_listing_id_and_observation_are_unique() -> None:
    assert Listing.__table__.columns["sreality_id"].unique is True

    observation_table = cast(Table, ListingObservation.__table__)
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in observation_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("listing_id", "run_id") in unique_columns


def test_nullable_fields_follow_profile() -> None:
    assert Listing.__table__.columns["price_czk"].nullable is True
    assert Listing.__table__.columns["building_area_m2"].nullable is True
    assert Listing.__table__.columns["description"].nullable is True
    assert Listing.__table__.columns["params_json"].nullable is False
    assert ScrapeRun.__table__.columns["finished_at"].nullable is True


def test_engine_requires_psycopg_postgresql_url() -> None:
    try:
        create_database_engine("sqlite+pysqlite:///:memory:")
    except ValueError as error:
        assert "postgresql+psycopg" in str(error)
    else:
        raise AssertionError("SQLite URL must not be accepted by the production DB adapter")
