from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import create_database_engine
from app.auth import models as auth_models  # noqa: F401
from app.citizens import models as citizen_models  # noqa: F401
from app.professionals import models as professional_models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import model modules above this line as they are introduced by each phase.
target_metadata = Base.metadata


def _database_url() -> str:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL must be configured before running database migrations."
        )
    return database_url


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""

    database_url = _database_url()
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured PostgreSQL database."""

    connectable: Engine = create_database_engine(_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        _run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
