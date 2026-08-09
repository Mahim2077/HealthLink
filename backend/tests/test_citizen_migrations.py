from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_phase_two_metadata_has_expected_tables_and_upgrade_compatible_check() -> None:
    assert {
        "user_national_identifiers",
        "citizen_profiles",
        "citizen_identifiers",
    }.issubset(Base.metadata.tables)
    identity_table = Base.metadata.tables["citizen_identifiers"]
    check_sql = {str(constraint.sqltext) for constraint in identity_table.constraints if hasattr(constraint, "sqltext")}
    assert (
        "national_identifier_id IS NOT NULL OR birth_certificate_number IS NOT NULL"
        in check_sql
    )


def test_phase_two_migrations_are_three_sequential_revisions() -> None:
    scripts = ScriptDirectory.from_config(Config(BACKEND_DIRECTORY / "alembic.ini"))

    assert scripts.get_revision("0003_user_national_identifiers").down_revision == (
        "0002_auth_sessions"
    )
    assert scripts.get_revision("0004_citizen_profiles").down_revision == (
        "0003_user_national_identifiers"
    )
    assert scripts.get_revision("0005_citizen_identifiers").down_revision == (
        "0004_citizen_profiles"
    )
    assert scripts.get_heads() == ["0005_citizen_identifiers"]
