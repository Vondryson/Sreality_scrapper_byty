"""Database engine and session construction."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create a PostgreSQL SQLAlchemy engine from an explicit URL."""
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("database_url must use the postgresql+psycopg driver")
    return create_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the application's non-expiring session factory."""
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a transactional session and rollback on failure."""
    with factory.begin() as session:
        yield session
