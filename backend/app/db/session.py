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
) -> Engine:
    options: dict[str, Any] = {"pool_pre_ping": True}
    if poolclass is not None:
        options["poolclass"] = poolclass
    return create_engine(normalize_database_url(database_url), **options)


@lru_cache
def get_engine() -> Engine:
    return create_database_engine(get_settings().database_url)


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
