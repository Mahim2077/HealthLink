from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.db.base import Base
from app.db.session import create_database_engine


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_phase_one_metadata_contains_only_shared_auth_tables() -> None:
    assert {"users", "auth_sessions"}.issubset(Base.metadata.tables)
    assert "active_professional_role_registration_id" in (
        Base.metadata.tables["auth_sessions"].columns
    )


def test_alembic_loads_phase_one_shared_auth_migration() -> None:
    config = Config(BACKEND_DIRECTORY / "alembic.ini")
    scripts = ScriptDirectory.from_config(config)

    users_revision = scripts.get_revision("0001_users")
    sessions_revision = scripts.get_revision("0002_auth_sessions")

    assert users_revision is not None
    assert users_revision.down_revision is None
    assert sessions_revision is not None
    assert sessions_revision.down_revision == "0001_users"


def test_sqlite_ignores_postgresql_prepared_statement_option() -> None:
    engine = create_database_engine(
        "sqlite+pysqlite:///:memory:",
        disable_prepared_statements=True,
    )

    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
