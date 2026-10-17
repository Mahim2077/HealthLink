from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, AppointmentQueueEntry, DoctorPracticeSession
from app.auth.constants import Portal
from app.auth.dependencies import AuthContext
from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.professionals.models import ProfessionalRoleRegistration
from app.visits.models import PatientAccessGrant

SCOPE_RESOURCES = {
    "FULL_MEDICAL_HISTORY": frozenset({"VISIT", "PRESCRIPTION", "LAB_REPORT", "EMERGENCY_PROFILE", "MEDICAL_HISTORY"}),
    "VISITS_ONLY": frozenset({"VISIT"}),
    "PRESCRIPTIONS_ONLY": frozenset({"PRESCRIPTION"}),
    "LAB_REPORTS_ONLY": frozenset({"LAB_REPORT"}),
    "EMERGENCY_PROFILE_ONLY": frozenset({"EMERGENCY_PROFILE"}),
}


@dataclass(frozen=True)
class ClinicalReadDecision:
    source: str
    grant_id: UUID | None = None
    role_registration_id: UUID | None = None


class ClinicalReadPolicy:
    """Read authority only. Never use this policy for clinical mutations."""

    def __init__(self, db: Session):
        self.db = db

    def doctor(self, auth: AuthContext) -> ProfessionalRoleRegistration:
        role_id = auth.session.active_professional_role_registration_id
        registration = self.db.get(ProfessionalRoleRegistration, role_id) if role_id else None
        if (auth.portal != Portal.PROFESSIONAL or not auth.user.is_active
            or role_id != auth.claims.active_professional_role_registration_id
            or registration is None or registration.professional.user_id != auth.user.id
            or registration.verification_status != "VERIFIED"
            or not registration.role.is_active or registration.role.code != "DOCTOR"):
            raise HealthLinkError("Verified Doctor role required.", status_code=403)
        return registration

    def authorize(self, auth: AuthContext, citizen_id: UUID, resource_type: str,
                  resource_id: UUID | None = None, author_role_id: UUID | None = None,
                  finalized: bool = True) -> ClinicalReadDecision:
        if resource_type not in SCOPE_RESOURCES["FULL_MEDICAL_HISTORY"]:
            raise HealthLinkError("Clinical record not found.", status_code=404)
        if auth.portal == Portal.CITIZEN:
            citizen = self.db.get(CitizenProfile, citizen_id)
            if citizen and citizen.user_id == auth.user.id and auth.user.is_active and finalized:
                return ClinicalReadDecision("SELF")
            raise HealthLinkError("Clinical record not found.", status_code=404)
        registration = self.doctor(auth)
        current = self.db.scalar(select(Appointment.id)
            .join(AppointmentQueueEntry, AppointmentQueueEntry.appointment_id == Appointment.id)
            .join(DoctorPracticeSession, DoctorPracticeSession.id == AppointmentQueueEntry.practice_session_id)
            .where(Appointment.citizen_id == citizen_id,
                   Appointment.doctor_role_registration_id == registration.id,
                   DoctorPracticeSession.doctor_role_registration_id == registration.id,
                   Appointment.facility_id == DoctorPracticeSession.facility_id,
                   Appointment.appointment_date == DoctorPracticeSession.session_date,
                   Appointment.status == "BOOKED", DoctorPracticeSession.status == "ACTIVE",
                   AppointmentQueueEntry.queue_status == "CURRENT").limit(1))
        if current:
            return ClinicalReadDecision("CURRENT_PATIENT", role_registration_id=registration.id)
        if finalized and resource_id is not None and author_role_id == registration.id and resource_type in {"VISIT", "PRESCRIPTION"}:
            return ClinicalReadDecision("AUTHOR", role_registration_id=registration.id)
        if finalized:
            scopes = [scope for scope, resources in SCOPE_RESOURCES.items() if resource_type in resources]
            grant = self.db.scalar(select(PatientAccessGrant).where(
                PatientAccessGrant.citizen_id == citizen_id,
                PatientAccessGrant.professional_role_registration_id == registration.id,
                PatientAccessGrant.access_scope.in_(scopes), PatientAccessGrant.revoked_at.is_(None),
                or_(PatientAccessGrant.expires_at.is_(None), PatientAccessGrant.expires_at > datetime.now(UTC)))
                .order_by(PatientAccessGrant.granted_at.desc(), PatientAccessGrant.id).limit(1))
            if grant:
                return ClinicalReadDecision("GRANT", grant.id, registration.id)
        raise HealthLinkError("Clinical record not found.", status_code=404)
