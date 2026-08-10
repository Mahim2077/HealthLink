from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, URL, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool

from app.core.config import get_settings


def normalize_database_url(database_url: str) -> URL:
    """Use psycopg 3 for standard PostgreSQL/Neon connection URLs."""

    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured before database access.")

    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url


def create_database_engine(
    database_url: str,
    *,
    poolclass: type[Pool] | None = None,
    disable_prepared_statements: bool = False,
) -> Engine:
    """Create a SQLAlchemy Engine wired to the HealthLink backend.

    Parameters
    ----------
    database_url:
        The connection string (any driver in ``URL.drivername``).
    poolclass:
        Optional pool implementation (typically ``NullPool`` for tests).
    disable_prepared_statements:
        When True, the engine is created with SQLAlchemy's
        ``statement_cache_size=0`` flag. This is required for
        PgBouncer-compatible transaction-mode poolers (e.g. Supabase's
        session pooler on port 6543) which reject the named prepared
        statements SQLAlchemy would otherwise cache per connection.
    """

    options: dict[str, Any] = {}
    if poolclass is None:
        # Only the production engine needs pre-ping; per-test engines
        # built on a fresh NullPool acquire a new connection every time
        # and never reuse a stale backend.
        options["pool_pre_ping"] = True
    if poolclass is not None:
        options["poolclass"] = poolclass
    url = normalize_database_url(database_url)
    if disable_prepared_statements:
        # PgBouncer transaction-mode poolers (e.g. Supabase session
        # pooler on port 6543) reject named prepared statements when the
        # same statement name lands on a different pooled backend. We
        # disable BOTH:
        #   * SQLAlchemy's compiled statement cache (statement_cache_size=0)
        #   * psycopg 3's automatic PREPARE on individual connections
        #     (prepare_threshold=None) so every statement is sent as a
        #     plain SQL string. Note: prepare_threshold=0 actually means
        #     "prepare every statement the first time it is executed",
        #     which is the opposite of what we want here.
        options["execution_options"] = {"statement_cache_size": 0}
        options["connect_args"] = {"prepare_threshold": None}
    return create_engine(url, **options)


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_database_engine(
        settings.database_url,
        disable_prepared_statements=settings.db_disable_prepared_statements,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing one SQLAlchemy session per request."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
