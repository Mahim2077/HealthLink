from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_phase_zero_metadata_has_no_feature_tables() -> None:
    assert list(Base.metadata.tables) == []


def test_alembic_loads_empty_phase_zero_migration_history() -> None:
    config = Config(BACKEND_DIRECTORY / "alembic.ini")
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == []
