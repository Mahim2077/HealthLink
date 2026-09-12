"""Exercise diagnostic row locks on an isolated local PostgreSQL schema."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
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
