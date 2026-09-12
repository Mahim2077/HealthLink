import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.appointments.models import AppointmentStatus, DoctorPracticeSession, SessionStatus
from app.auth.dependencies import AuthContext
from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.diagnostics.models import DiagnosticTest
from app.diagnostics.report_models import LabReport, LabReportItem
from app.diagnostics.report_schemas import LabItemInput, LabReportInput, LabReportView, LabTrendPoint
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.models import ProfessionalRoleRegistration
from app.professionals.repository import ProfessionalRepository
from app.visits.repository import VisitsRepository


class LabReportService:
    def __init__(self, db: Session):
        self.db = db

    def _test(self, test_id: uuid.UUID, lock=False):
        stmt = select(DiagnosticTest).where(DiagnosticTest.id == test_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        test = self.db.scalar(stmt)
        if test is None:
            raise HealthLinkError("Diagnostic test not found.", status_code=404)
        return test

    def _report(self, test_id, lock=False):
        stmt = select(LabReport).where(LabReport.diagnostic_test_id == test_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return self.db.scalar(stmt)

    def _assigned(self, test, actor):
        if test.assigned_to_role_registration_id != actor.id:
            raise HealthLinkError("Diagnostic test not found.", status_code=404)
        if actor.facility_id != test.facility_id:
            raise HealthLinkError("The assigned facility context has changed.", status_code=403)
        facility = self.db.get(HealthcareFacility, test.facility_id)
        if not facility or not facility.is_active:
            raise HealthLinkError("The diagnostic facility is inactive.", status_code=403)

    def save(self, test_id: uuid.UUID, actor: ProfessionalRoleRegistration, payload: LabReportInput):
        test = self._test(test_id, lock=True)
        self._assigned(test, actor)
        report = self._report(test_id, lock=True)
        if test.status != "IN_PROGRESS" or (report is not None and report.status != "DRAFT"):
            raise HealthLinkError("Only an in-progress test's draft report can be edited.", status_code=409)
        if report is None:
            report = LabReport(diagnostic_test_id=test.id, citizen_id=test.citizen_id, facility_id=test.facility_id, created_by_role_registration_id=actor.id, report_date=payload.report_date)
            self.db.add(report)
            self.db.flush()
        report.report_date, report.summary = payload.report_date, payload.summary
        self.db.execute(delete(LabReportItem).where(LabReportItem.lab_report_id == report.id))
        self.db.add_all(LabReportItem(lab_report_id=report.id, **item.model_dump()) for item in payload.items)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.view(report, test)

    def finalize(self, test_id, actor):
        # Both save and finalize lock the test before the report, consistently.
        test = self._test(test_id, lock=True)
        self._assigned(test, actor)
        report = self._report(test_id, lock=True)
        if report is None or report.status != "DRAFT" or test.status != "IN_PROGRESS":
            raise HealthLinkError("An in-progress test with a saved draft report is required.", status_code=409)
        if not self.db.scalar(select(LabReportItem.id).where(LabReportItem.lab_report_id == report.id).limit(1)):
            raise HealthLinkError("At least one report item is required.", status_code=409)
        report.status = "FINALIZED"
        report.finalized_at = datetime.now(timezone.utc)
        test.status = "COMPLETED"
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.view(report, test)

    def read(self, test_id, auth: AuthContext):
        test = self._test(test_id)
        report = self._report(test_id)
        allowed = False
        if auth.session.portal == Portal.CITIZEN.value:
            citizen = self.db.scalar(select(CitizenProfile).where(CitizenProfile.user_id == auth.user.id))
            allowed = citizen is not None and citizen.id == test.citizen_id and report is not None and report.status == "FINALIZED"
        elif auth.session.portal == Portal.PROFESSIONAL.value:
            role_id = auth.session.active_professional_role_registration_id
            role = ProfessionalRepository(self.db).get_role_registration_by_id(role_id) if role_id and role_id == auth.claims.active_professional_role_registration_id else None
            if role and role.professional.user_id == auth.user.id and role.verification_status == "VERIFIED" and role.role.is_active:
                if role.role.code == ProfessionalRoleCode.LAB_TECHNICIAN.value:
                    self._assigned(test, role)
                    allowed = True
                elif role.role.code == ProfessionalRoleCode.DOCTOR.value and report and report.status == "FINALIZED":
                    current = VisitsRepository(self.db).load_current_patient_for_doctor(auth.user.id)
                    session = self.db.get(DoctorPracticeSession, current.queue_entry.practice_session_id) if current else None
                    allowed = bool(current and session and current.citizen.id == test.citizen_id and current.appointment.doctor_role_registration_id == role.id and current.appointment.status == AppointmentStatus.BOOKED.value and session.status == SessionStatus.ACTIVE.value)
        if not allowed:
            raise HealthLinkError("Lab report not found.", status_code=404)
        return self.view(report, test) if report else None

    def list_citizen(self, citizen_id, page: int):
        rows = self.db.execute(select(LabReport, DiagnosticTest).join(DiagnosticTest, DiagnosticTest.id == LabReport.diagnostic_test_id).where(LabReport.citizen_id == citizen_id, LabReport.status == "FINALIZED").order_by(LabReport.report_date.desc(), LabReport.id.desc()).offset((page - 1) * 20).limit(20)).all()
        return [self.view(report, test) for report, test in rows]

    def trends(self, citizen_id, page: int):
        rows = self.db.execute(select(LabReport, LabReportItem).join(LabReportItem, LabReportItem.lab_report_id == LabReport.id).where(LabReport.citizen_id == citizen_id, LabReport.status == "FINALIZED", LabReportItem.result_value_numeric.is_not(None)).order_by(LabReport.report_date, LabReport.id, LabReportItem.id).offset((page - 1) * 100).limit(100)).all()
        return [LabTrendPoint(report_id=report.id, report_date=report.report_date, parameter_name=item.parameter_name, value=item.result_value_numeric, unit=item.unit) for report, item in rows]

    def view(self, report, test):
        items = self.db.scalars(select(LabReportItem).where(LabReportItem.lab_report_id == report.id).order_by(LabReportItem.parameter_name, LabReportItem.id)).all()
        facility = self.db.get(HealthcareFacility, report.facility_id) if report.facility_id else None
        return LabReportView(id=report.id, diagnostic_test_id=test.id, citizen_id=report.citizen_id, status=report.status, finalized_at=report.finalized_at, report_date=report.report_date, summary=report.summary, test_name=test.test_name, facility_name=facility.name if facility else None, items=[LabItemInput(parameter_name=item.parameter_name, result_value_text=item.result_value_text, result_value_numeric=item.result_value_numeric, unit=item.unit, reference_range=item.reference_range, flag=item.flag) for item in items])
