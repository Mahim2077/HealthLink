from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_phase_five_metadata_contains_exact_admin_foundation() -> None:
    assert {"admin_accounts", "admin_action_logs"}.issubset(Base.metadata.tables)
    account = Base.metadata.tables["admin_accounts"]
    log = Base.metadata.tables["admin_action_logs"]
    assert account.c.user_id.unique
    assert log.c.action_type.type.length == 100
    assert log.c.reason.nullable


def test_phase_five_migrations_follow_phase_four() -> None:
    scripts = ScriptDirectory.from_config(Config(BACKEND_DIRECTORY / "alembic.ini"))
    assert scripts.get_revision("0010_admin_accounts").down_revision == "0009_doctor_reg_details"
    assert scripts.get_revision("0011_admin_action_logs").down_revision == "0010_admin_accounts"
    assert scripts.get_heads() == ["0011_admin_action_logs"]
