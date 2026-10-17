from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, AppointmentQueueEntry, DoctorPracticeSession
from app.clinical_audit.service import AuditService
from app.dashboards.schemas import AdminOverview, ChamberOverview, CitizenOverview, ProfessionalOverview, RecentPrescription, RecentReport, UpcomingAppointment
from app.diagnostics.models import DiagnosticTest
from app.diagnostics.report_models import LabReport
from app.emergency.models import EmergencyProfile
from app.facilities.models import HealthcareFacility
from app.prescriptions.models import Prescription
from app.professionals.models import ProfessionalRoleRegistration
from app.reminders.models import MedicineReminder, Notification
from app.visits.models import MedicalVisit


def care_today():
    return datetime.now(ZoneInfo("Asia/Dhaka")).date()


class DashboardService:
    """Only metadata: no model generation, queue mutation or clinical text."""
    def __init__(self, db: Session):
        self.db = db

    def _count(self, model, *conditions):
        return self.db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0

    def _recent_prescription(self, *conditions):
        return self.db.scalar(select(Prescription)
            .join(MedicalVisit, MedicalVisit.id == Prescription.visit_id)
            .where(MedicalVisit.status == "FINALIZED", *conditions)
            .order_by(Prescription.created_at.desc(), Prescription.id.desc()).limit(1))

    def citizen(self, context):
        citizen_id, today = context.profile.id, care_today()
        upcoming = self.db.execute(select(Appointment, HealthcareFacility.name)
            .join(HealthcareFacility, HealthcareFacility.id == Appointment.facility_id)
            .where(Appointment.citizen_id == citizen_id, Appointment.status == "BOOKED", Appointment.appointment_date >= today)
            .order_by(Appointment.appointment_date, Appointment.serial_number, Appointment.id).limit(1)).first()
        prescription = self._recent_prescription(Prescription.citizen_id == citizen_id, MedicalVisit.citizen_id == citizen_id)
        report = self.db.execute(select(LabReport, DiagnosticTest.test_name)
            .join(DiagnosticTest, DiagnosticTest.id == LabReport.diagnostic_test_id)
            .where(LabReport.citizen_id == citizen_id, DiagnosticTest.citizen_id == citizen_id, LabReport.status == "FINALIZED")
            .order_by(LabReport.report_date.desc(), LabReport.finalized_at.desc(), LabReport.id.desc()).limit(1)).first()
        updated = self.db.scalar(select(EmergencyProfile.updated_at).where(EmergencyProfile.citizen_id == citizen_id))
        result = CitizenOverview(today=today,
            upcoming_appointment=UpcomingAppointment(id=upcoming[0].id, appointment_date=upcoming[0].appointment_date,
                serial_number=upcoming[0].serial_number, facility_name=upcoming[1]) if upcoming else None,
            recent_prescription=RecentPrescription.model_validate(prescription, from_attributes=True) if prescription else None,
            latest_report=RecentReport(diagnostic_test_id=report[0].diagnostic_test_id, test_name=report[1], report_date=report[0].report_date) if report else None,
            active_reminders=self._count(MedicineReminder, MedicineReminder.citizen_id == citizen_id,
                MedicineReminder.is_active.is_(True), MedicineReminder.start_date <= today,
                or_(MedicineReminder.end_date.is_(None), MedicineReminder.end_date >= today)),
            unread_notifications=self._count(Notification, Notification.citizen_id == citizen_id, Notification.read_at.is_(None)),
            emergency_profile_updated_at=updated)
        AuditService(self.db).record(auth=context.auth, citizen_id=citizen_id,
            resource_type="CARE_OVERVIEW", access_source="CITIZEN_SELF")
        return result

    def professional(self, context):
        registration, today = context.role_registration, care_today()
        doctor = registration.role.code == "DOCTOR"
        owner = DiagnosticTest.requested_by_role_registration_id if doctor else DiagnosticTest.assigned_to_role_registration_id
        scope = [owner == registration.id]
        if not doctor:
            facility = self.db.get(HealthcareFacility, registration.facility_id)
            scope.append(DiagnosticTest.facility_id == registration.facility_id)
            if facility is None or not facility.is_active:
                scope.append(DiagnosticTest.id.is_(None))
        chambers, has_more, recent = [], False, None
        if doctor:
            sessions = self.db.execute(select(DoctorPracticeSession, HealthcareFacility.name)
                .join(HealthcareFacility, HealthcareFacility.id == DoctorPracticeSession.facility_id)
                .where(DoctorPracticeSession.doctor_role_registration_id == registration.id, DoctorPracticeSession.session_date == today)
                .order_by(HealthcareFacility.name, DoctorPracticeSession.id).limit(11)).all()
            has_more = len(sessions) > 10
            for session, name in sessions[:10]:
                queue = (select(Appointment.serial_number)
                    .join(AppointmentQueueEntry, AppointmentQueueEntry.appointment_id == Appointment.id)
                    .where(AppointmentQueueEntry.practice_session_id == session.id,
                           Appointment.doctor_role_registration_id == registration.id,
                           Appointment.facility_id == session.facility_id,
                           Appointment.appointment_date == session.session_date,
                           Appointment.status == "BOOKED"))
                waiting_query = queue.where(AppointmentQueueEntry.queue_status == "WAITING")
                waiting = (self.db.scalar(select(func.count()).select_from(waiting_query.subquery())) or 0) if session.status != "COMPLETED" else 0
                serial = self.db.scalar(queue.where(AppointmentQueueEntry.queue_status == "CURRENT")
                    .order_by(Appointment.serial_number).limit(1)) if session.status == "ACTIVE" else None
                chambers.append(ChamberOverview(facility_name=name, status=session.status, waiting_count=waiting, current_serial=serial))
            prescription = self._recent_prescription(Prescription.author_doctor_role_registration_id == registration.id, MedicalVisit.doctor_role_registration_id == registration.id)
            if prescription:
                recent = RecentPrescription.model_validate(prescription, from_attributes=True)
                AuditService(self.db).record(auth=context.auth, citizen_id=prescription.citizen_id,
                    resource_type="PRESCRIPTION", resource_id=prescription.id, access_source="AUTHOR")
        def report_count(status):
            bounded = select(LabReport.id).join(DiagnosticTest, DiagnosticTest.id == LabReport.diagnostic_test_id).where(
                *scope, LabReport.created_by_role_registration_id == registration.id,
                LabReport.facility_id == registration.facility_id, LabReport.status == status)
            return self.db.scalar(select(func.count()).select_from(bounded.subquery())) or 0
        return ProfessionalOverview(today=today, role_code=registration.role.code, chambers=chambers, chambers_has_more=has_more,
            requested_tests=self._count(DiagnosticTest, *scope, DiagnosticTest.status == "REQUESTED"),
            in_progress_tests=self._count(DiagnosticTest, *scope, DiagnosticTest.status == "IN_PROGRESS"),
            draft_reports=report_count("DRAFT") if not doctor else 0,
            finalized_reports=report_count("FINALIZED") if not doctor else 0, recent_prescription=recent)

    def admin(self):
        return AdminOverview(
            pending_professional_registrations=self._count(ProfessionalRoleRegistration, ProfessionalRoleRegistration.verification_status == "PENDING"),
            active_facilities=self._count(HealthcareFacility, HealthcareFacility.is_active.is_(True)),
            facilities_needing_location=self._count(HealthcareFacility, HealthcareFacility.is_active.is_(True), HealthcareFacility.location_status != "CONFIRMED"))
