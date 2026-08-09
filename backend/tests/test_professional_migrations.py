from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def test_professional_metadata_includes_phase_six_facility_but_delays_active_role() -> None:
    expected = {
        "healthcare_professional_profiles",
        "professional_roles",
        "professional_role_registrations",
        "doctor_registration_details",
    }
    assert expected.issubset(Base.metadata.tables)
    registrations = Base.metadata.tables["professional_role_registrations"]
    assert "facility_id" in registrations.columns
    assert {
        foreign_key.target_fullname
        for foreign_key in registrations.c.facility_id.foreign_keys
    } == {"healthcare_facilities.id"}
    assert "active_professional_role_registration_id" not in Base.metadata.tables[
        "auth_sessions"
    ].columns


def test_phase_four_migrations_are_four_sequential_revisions() -> None:
    scripts = ScriptDirectory.from_config(Config(BACKEND_DIRECTORY / "alembic.ini"))
    expected = [
        ("0006_prof_profiles", "0005_citizen_identifiers"),
        ("0007_prof_roles", "0006_prof_profiles"),
        ("0008_prof_role_regs", "0007_prof_roles"),
        ("0009_doctor_reg_details", "0008_prof_role_regs"),
    ]
    for revision, parent in expected:
        assert scripts.get_revision(revision).down_revision == parent
    assert scripts.get_revision("0009_doctor_reg_details") is not None
