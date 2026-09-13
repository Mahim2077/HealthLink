"""Concurrent first-save safety on a loopback PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.emergency.models import EmergencyProfile
from app.emergency.schemas import EmergencyProfileInput
from app.emergency.service import EmergencyProfileService
from test_diagnostics import _citizen
from test_diagnostics_postgresql import diagnostic_pg_engine  # noqa: F401


def test_two_concurrent_first_saves_produce_one_complete_profile(diagnostic_pg_engine):
    with Session(diagnostic_pg_engine) as db:
        _, citizen = _citizen(db, "Emergency concurrency")
        citizen_id = citizen.id
    ready = Barrier(2)

    def save(value):
        with Session(diagnostic_pg_engine) as db:
            ready.wait(timeout=10)
            return EmergencyProfileService(db).save(citizen_id, EmergencyProfileInput(allergies=value, special_notes=value))

    with ThreadPoolExecutor(max_workers=2) as executor:
        tasks = [executor.submit(save, value) for value in ("first", "second")]
        results = [task.result(timeout=15) for task in tasks]
    assert len(results) == 2
    with Session(diagnostic_pg_engine) as db:
        rows = list(db.scalars(select(EmergencyProfile).where(EmergencyProfile.citizen_id == citizen_id)))
        assert len(rows) == 1
        assert rows[0].allergies in {"first", "second"}
        assert rows[0].allergies == rows[0].special_notes
