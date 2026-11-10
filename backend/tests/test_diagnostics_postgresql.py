"""Exercise diagnostic row locks on an isolated local PostgreSQL schema."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.exceptions import HealthLinkError
from app.db.base import Base
from app.diagnostics.models import DiagnosticTest, DiagnosticTestStatus
from app.diagnostics.service import DiagnosticsService
from app.diagnostics.report_service import LabReportService
from app.diagnostics.report_schemas import LabReportInput
from app.diagnostics.report_models import LabReport
from app.diagnostics.session_models import DiagnosticPdf, LabSession
from app.diagnostics.session_schemas import AcceptLabSession, CloseReason
from app.diagnostics.session_service import LabSessionService
from app.professionals.constants import ROLE_SEED_DATA, ProfessionalRoleCode
from app.professionals.models import ProfessionalRole, ProfessionalRoleRegistration
from test_diagnostics import _citizen, _facility, _queue, _registration


@pytest.fixture
def diagnostic_pg_engine():
    url = os.getenv("HEALTHLINK_TEST_DATABASE_URL")
    if not url or make_url(url).host not in ("localhost", "127.0.0.1", "::1"):
        pytest.skip("A local HEALTHLINK_TEST_DATABASE_URL is required")
    schema = "diagnostics_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all(ProfessionalRole(code=code.value, name=name, description=description) for code, name, description in ROLE_SEED_DATA)
            db.commit()
        yield engine
    finally:
        engine.dispose()
        # Exact random schema created by this fixture, on a loopback database only.
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_concurrent_begin_has_one_winner(diagnostic_pg_engine):
    with Session(diagnostic_pg_engine, expire_on_commit=False) as db:
        facility = _facility(db)
        _, doctor = _registration(db, facility, ProfessionalRoleCode.DOCTOR)
        _, lab = _registration(db, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
        _, citizen = _citizen(db, "Concurrent")
        visit = _queue(db, doctor, facility, citizen)
        test = DiagnosticTest(citizen_id=citizen.id, visit_id=visit.id, requested_by_role_registration_id=doctor.id, assigned_to_role_registration_id=lab.id, facility_id=facility.id, test_name="CBC")
        db.add(test)
        db.commit()
        test_id, lab_id = test.id, lab.id
    barrier = Barrier(2)

    def begin():
        with Session(diagnostic_pg_engine) as db:
            actor = db.get(ProfessionalRoleRegistration, lab_id)
            barrier.wait(timeout=10)
            try:
                return DiagnosticsService(db).transition(test_id, actor, DiagnosticTestStatus.IN_PROGRESS).status.value
            except HealthLinkError as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(begin) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results.count("IN_PROGRESS") == 1
    assert results.count(409) == 1
    with Session(diagnostic_pg_engine) as db:
        assert db.scalar(select(DiagnosticTest.status).where(DiagnosticTest.id == test_id)) == "IN_PROGRESS"


def test_concurrent_session_acceptance_and_terminal_actions(diagnostic_pg_engine):
    with Session(diagnostic_pg_engine, expire_on_commit=False) as db:
        facility = _facility(db)
        _, first = _registration(db, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
        _, second = _registration(db, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
        _, citizen = _citizen(db, "Session race")
        item = LabSession(citizen_id=citizen.id, catalog_code="CBC", share_code="a-short-lived-test-code")
        db.add(item)
        db.commit()
        session_id, code, lab_ids = item.id, item.share_code, (first.id, second.id)

    def compete(actions):
        barrier = Barrier(2)

        def run(action):
            with Session(diagnostic_pg_engine) as db:
                barrier.wait(timeout=10)
                try:
                    return action(LabSessionService(db), db).status.value
                except HealthLinkError as error:
                    return error.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run, action) for action in actions]
            return [future.result(timeout=15) for future in futures]

    def accept(lab_id):
        return lambda service, db: service.accept(
            db.get(ProfessionalRoleRegistration, lab_id),
            AcceptLabSession(code=code, attendance_deadline=datetime.now(UTC) + timedelta(hours=1)),
            None,
        )

    assert set(compete([accept(lab_id) for lab_id in lab_ids])) == {"ACCEPTED", 404}
    with Session(diagnostic_pg_engine) as db:
        item = db.get(LabSession, session_id)
        assigned_id = item.technician_id
        item.status = "PERFORMED"
        db.add(DiagnosticPdf(session_id=session_id, version=1, catalog_code="CBC", tested_at=datetime.now(UTC),
                             sha256="f" * 64, content=b"synthetic race fixture"))
        db.commit()

    results = compete([
        lambda service, db: service.close(session_id, CloseReason.STAFF, None, actor=db.get(ProfessionalRoleRegistration, assigned_id)),
        lambda service, db: service.publish(session_id, 1, db.get(ProfessionalRoleRegistration, assigned_id), None),
    ])
    assert set(results) in ({"UNABLE", 409}, {"PUBLISHED", 409})
    with Session(diagnostic_pg_engine) as db:
        item = db.get(LabSession, session_id)
        assert (item.current_report_version == 1) == (item.status == "PUBLISHED")


def test_concurrent_report_finalization_has_one_winner(diagnostic_pg_engine):
    from test_lab_reports import payload
    with Session(diagnostic_pg_engine, expire_on_commit=False) as db:
        facility = _facility(db)
        _, doctor = _registration(db, facility, ProfessionalRoleCode.DOCTOR)
        _, lab = _registration(db, facility, ProfessionalRoleCode.LAB_TECHNICIAN)
        _, citizen = _citizen(db, "Report concurrency")
        visit = _queue(db, doctor, facility, citizen)
        test = DiagnosticTest(citizen_id=citizen.id, visit_id=visit.id, requested_by_role_registration_id=doctor.id, assigned_to_role_registration_id=lab.id, facility_id=facility.id, test_name="CBC", status="IN_PROGRESS")
        db.add(test); db.commit()
        LabReportService(db).save(test.id, lab, LabReportInput.model_validate(payload()))
        test_id, lab_id = test.id, lab.id
    barrier = Barrier(2)

    def finalize():
        with Session(diagnostic_pg_engine) as db:
            actor = db.get(ProfessionalRoleRegistration, lab_id)
            barrier.wait(timeout=10)
            try:
                return LabReportService(db).finalize(test_id, actor).status
            except HealthLinkError as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(finalize) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results.count("FINALIZED") == 1 and results.count(409) == 1
    with Session(diagnostic_pg_engine) as db:
        report = db.scalar(select(LabReport).where(LabReport.diagnostic_test_id == test_id))
        assert report.status == "FINALIZED" and report.finalized_at is not None
        assert db.get(DiagnosticTest, test_id).status == "COMPLETED"
