"""Alembic runtime configuration."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from sreality_tracker.db import models  # noqa: F401
from sreality_tracker.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = config.attributes.get("database_url") or os.getenv("SREALITY_DATABASE_URL")
if database_url:
    if not isinstance(database_url, str):
        raise TypeError("Alembic database_url attribute must be a string")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a PostgreSQL connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        expected_database = config.attributes.get("expected_database")
        actual_database = connection.engine.url.database
        if expected_database is not None and actual_database != expected_database:
            raise RuntimeError(
                f"Refusing migration: expected database {expected_database!r}, "
                f"connected to {actual_database!r}"
            )
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
