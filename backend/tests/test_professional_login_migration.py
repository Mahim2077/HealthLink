from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_phase_seven_active_role_migration_and_fk() -> None:
    scripts = ScriptDirectory.from_config(Config(BACKEND_DIRECTORY / "alembic.ini"))
    revision = scripts.get_revision("0014_auth_active_role")
    assert revision.down_revision == "0013_role_facility_fk"
    assert scripts.get_revision("0018_appointment_queue_entries") is not None
    assert scripts.get_revision("0020_medical_visits") is not None
    assert scripts.get_revision("0023_prescription_documents") is not None
    # The head moves forward as Phase 11+, 12, 13, 14 each append
    # migrations; only require the *latest* one here. Phase 13 added
    # the prescription chain (0021-0023) so the current head is
    # ``0023_prescription_documents``.
    assert scripts.get_heads() == ["0023_prescription_documents"]
    column = Base.metadata.tables["auth_sessions"].c.active_professional_role_registration_id
    assert column.nullable is True
    assert {fk.target_fullname for fk in column.foreign_keys} == {
        "professional_role_registrations.id"
    }
