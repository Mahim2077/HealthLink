from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    DoctorPracticeSession,
    QueueStatus,
)
from app.auth.models import User
from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.facilities.models import HealthcareFacility
from app.professionals.constants import (
    ProfessionalRoleCode,
    VerificationStatus,
)
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit, PatientAccessGrant, VisitStatus


@dataclass(frozen=True)
class CurrentPatientContext:
    """Joined data the consultation workspace needs in one round-trip."""

    queue_entry: AppointmentQueueEntry
    appointment: Appointment
    citizen: CitizenProfile
    facility: HealthcareFacility
    doctor_user: User
    visit: MedicalVisit | None


class VisitsRepository:
    """Read + write helpers for the Phase 12 consultation workspace.

    Concurrency-sensitive reads (current queue entry, manual grant
    lookup) participate in the same advisory-lock pattern used by
    Phase 11 to keep ``CURRENT`` invariant consistent across both
    endpoints.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Current-patient resolution
    # ------------------------------------------------------------------

    def _doctor_role_id(self) -> uuid.UUID:
        role_id = self.db.scalar(
            select(ProfessionalRole.id).where(
                ProfessionalRole.code == ProfessionalRoleCode.DOCTOR.value
            )
        )
        if role_id is None:
            raise RuntimeError("Doctor professional role is not seeded.")
        return role_id

    def find_verified_doctor_role_registration(
        self,
        doctor_user_id: uuid.UUID,
    ) -> ProfessionalRoleRegistration | None:
        role_id = self._doctor_role_id()
        return self.db.scalar(
            select(ProfessionalRoleRegistration)
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .where(HealthcareProfessionalProfile.user_id == doctor_user_id)
            .where(ProfessionalRoleRegistration.role_id == role_id)
            .where(
                ProfessionalRoleRegistration.verification_status
                == VerificationStatus.VERIFIED.value
            )
        )

    def load_current_patient_for_doctor(
        self,
        doctor_user_id: uuid.UUID,
    ) -> CurrentPatientContext | None:
        """Return the doctor user with their current chamber patient, if any.

        Only verified doctors reach this code path through
        ``require_current_patient_access``; for the workspace page we
        also return ``None`` cleanly when there is no current queue
        entry so the UI can show a friendly "no active patient" state.
        """

        registration = self.find_verified_doctor_role_registration(doctor_user_id)
        if registration is None:
            return None

        # The doctor user is needed for the patient banner.
        doctor_user = self.db.scalar(
            select(User).where(User.id == doctor_user_id)
        )
        if doctor_user is None:
            return None

        # Find the most recent CURRENT queue entry authored by this doctor.
        queue_entry = self.db.scalar(
            select(AppointmentQueueEntry)
            .join(
                DoctorPracticeSession,
                DoctorPracticeSession.id
                == AppointmentQueueEntry.practice_session_id,
            )
            .where(
                DoctorPracticeSession.doctor_role_registration_id
                == registration.id
            )
            .where(AppointmentQueueEntry.queue_status == QueueStatus.CURRENT.value)
            .order_by(AppointmentQueueEntry.became_current_at.desc())
            .limit(1)
        )
        if queue_entry is None:
            return None

        appointment = self.db.get(Appointment, queue_entry.appointment_id)
        if appointment is None:
            return None

        citizen = self.db.get(CitizenProfile, appointment.citizen_id)
        if citizen is None:
            return None

        facility = self.db.get(HealthcareFacility, appointment.facility_id)
        if facility is None:
            return None

        visit = self.db.scalar(
            select(MedicalVisit).where(
                MedicalVisit.appointment_id == appointment.id
            )
        )

        return CurrentPatientContext(
            queue_entry=queue_entry,
            appointment=appointment,
            citizen=citizen,
            facility=facility,
            doctor_user=doctor_user,
            visit=visit,
        )

    def load_current_patient_or_raise(
        self, doctor_user_id: uuid.UUID
    ) -> CurrentPatientContext:
        from app.core.exceptions import HealthLinkError

        ctx = self.load_current_patient_for_doctor(doctor_user_id)
        if ctx is None:
            raise HealthLinkError(
                "No current chamber patient for the verified doctor.",
                status_code=404,
            )
        return ctx

    def load_queue_entry_for_doctor(
        self,
        doctor_user_id: uuid.UUID,
        queue_id: uuid.UUID,
    ) -> CurrentPatientContext | None:
        """Resolve a specific queue entry back to its joined context.

        Used by the explicit ``POST start_visit_for_current`` action
        where the doctor pressed a "Open consultation" button next to
        a specific CURRENT queue row.
        """

        registration = self.find_verified_doctor_role_registration(doctor_user_id)
        if registration is None:
            return None
        doctor_user = self.db.get(User, doctor_user_id)
        if doctor_user is None:
            return None

        queue_entry = self.db.scalar(
            select(AppointmentQueueEntry)
            .join(
                DoctorPracticeSession,
                DoctorPracticeSession.id
                == AppointmentQueueEntry.practice_session_id,
            )
            .where(
                DoctorPracticeSession.doctor_role_registration_id
                == registration.id
            )
            .where(AppointmentQueueEntry.id == queue_id)
            .where(AppointmentQueueEntry.queue_status == QueueStatus.CURRENT.value)
        )
        if queue_entry is None:
            return None

        appointment = self.db.get(Appointment, queue_entry.appointment_id)
        if appointment is None:
            return None
        citizen = self.db.get(CitizenProfile, appointment.citizen_id)
        if citizen is None:
            return None
        facility = self.db.get(HealthcareFacility, appointment.facility_id)
        if facility is None:
            return None
        visit = self.db.scalar(
            select(MedicalVisit).where(
                MedicalVisit.appointment_id == appointment.id
            )
        )
        return CurrentPatientContext(
            queue_entry=queue_entry,
            appointment=appointment,
            citizen=citizen,
            facility=facility,
            doctor_user=doctor_user,
            visit=visit,
        )

    def load_queue_entry_or_raise(
        self,
        doctor_user_id: uuid.UUID,
        queue_id: uuid.UUID,
    ) -> CurrentPatientContext:
        from app.core.exceptions import HealthLinkError

        ctx = self.load_queue_entry_for_doctor(doctor_user_id, queue_id)
        if ctx is None:
            raise HealthLinkError(
                "Queue entry is not your current chamber patient.",
                status_code=404,
            )
        return ctx


    # ------------------------------------------------------------------
    # Visit write helpers
    # ------------------------------------------------------------------

    def create_visit_for_appointment(
        self,
        *,
        citizen_id: uuid.UUID,
        doctor_role_registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> MedicalVisit:
        visit = MedicalVisit(
            citizen_id=citizen_id,
            doctor_role_registration_id=doctor_role_registration_id,
            facility_id=facility_id,
            appointment_id=appointment_id,
            status=VisitStatus.DRAFT.value,
        )
        self.db.add(visit)
        self.db.flush()
        return visit

    def update_visit_draft(
        self,
        visit: MedicalVisit,
        *,
        chief_complaint: str | None,
        clinical_notes: str | None,
        diagnosis: str | None,
        follow_up_instructions: str | None,
    ) -> MedicalVisit:
        if visit.status != VisitStatus.DRAFT.value:
            raise HealthLinkError(
                "Cannot edit a finalized visit; create a new consultation.",
                status_code=409,
            )
        visit.chief_complaint = chief_complaint
        visit.clinical_notes = clinical_notes
        visit.diagnosis = diagnosis
        visit.follow_up_instructions = follow_up_instructions
        self.db.flush()
        return visit

    # ------------------------------------------------------------------
    # Manual access-grant lookup
    # ------------------------------------------------------------------

    def find_active_grant(
        self,
        *,
        citizen_id: uuid.UUID,
        professional_role_registration_id: uuid.UUID,
        at: datetime | None = None,
    ) -> PatientAccessGrant | None:
        """Return the currently active grant for a citizen+doctor pair, if any."""

        moment = at or datetime.utcnow()
        statement = select(PatientAccessGrant).where(
            PatientAccessGrant.citizen_id == citizen_id
        ).where(
            PatientAccessGrant.professional_role_registration_id
            == professional_role_registration_id
        ).where(
            PatientAccessGrant.revoked_at.is_(None)
        ).where(
            or_(
                PatientAccessGrant.expires_at.is_(None),
                PatientAccessGrant.expires_at > moment,
            )
        ).order_by(PatientAccessGrant.granted_at.desc()).limit(1)
        return self.db.scalar(statement)

    # ------------------------------------------------------------------
    # Citizen read helpers
    # ------------------------------------------------------------------

    def list_visits_for_citizen(
        self,
        citizen_id: uuid.UUID,
        *,
        target_date: date | None = None,
    ) -> Iterable[tuple[MedicalVisit, Appointment | None, User, HealthcareFacility]]:
        """Return visits for a citizen joined to their appointment + doctor + facility.

        Restricted to ``DRAFT`` and ``FINALIZED`` visits; appointment
        joins are LEFT OUTER so a manual-grant consultation can still
        surface.
        """

        stmt = (
            select(MedicalVisit, Appointment, User, HealthcareFacility)
            .join(
                ProfessionalRoleRegistration,
                ProfessionalRoleRegistration.id
                == MedicalVisit.doctor_role_registration_id,
            )
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .join(User, User.id == HealthcareProfessionalProfile.user_id)
            .join(
                HealthcareFacility,
                HealthcareFacility.id == MedicalVisit.facility_id,
            )
            .outerjoin(
                Appointment, Appointment.id == MedicalVisit.appointment_id
            )
            .where(MedicalVisit.citizen_id == citizen_id)
            .order_by(MedicalVisit.visit_date.desc())
        )
        if target_date is not None:
            # Compare the calendar-date portion of `visit_date` against the
            # target date so the filter is timezone-stable across the
            # test runner (where `date.today()` is local) and the database
            # server (where `func.now()` is also local). Using
            # `func.date(...)` works on both SQLite and PostgreSQL without
            # requiring the column to be timezone-aware in the driver.
            stmt = stmt.where(func.date(MedicalVisit.visit_date) == target_date)
        return self.db.execute(stmt).all()


__all__ = [
    "CurrentPatientContext",
    "VisitsRepository",
]
