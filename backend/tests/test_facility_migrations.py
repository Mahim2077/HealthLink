from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint

from app.db.base import Base


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_phase_six_migration_chain_and_metadata() -> None:
    scripts = ScriptDirectory.from_config(Config(BACKEND_DIRECTORY / "alembic.ini"))
    assert scripts.get_revision("0012_facilities").down_revision == "0011_admin_action_logs"
    assert scripts.get_revision("0013_role_facility_fk").down_revision == "0012_facilities"
    assert scripts.get_heads() == ["0013_role_facility_fk"]

    facilities = Base.metadata.tables["healthcare_facilities"]
    assert {
        "id", "name", "facility_type", "registration_number", "address",
        "phone", "email", "is_active", "created_at", "updated_at",
    } == set(facilities.columns.keys())
    assert facilities.c.name.type.length == 200
    assert facilities.c.facility_type.type.length == 50
    assert facilities.c.address.nullable is False
    checks = {
        str(item.sqltext)
        for item in facilities.constraints
        if isinstance(item, CheckConstraint)
    }
    assert any("DIAGNOSTIC_CENTER" in item and "PHARMACY" in item for item in checks)
    registrations = Base.metadata.tables["professional_role_registrations"]
    targets = {fk.target_fullname for fk in registrations.c.facility_id.foreign_keys}
    assert targets == {"healthcare_facilities.id"}
    assert registrations.c.facility_id.nullable is True
