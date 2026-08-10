from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.auth.models import User
from app.citizens.models import CitizenProfile
from app.core.exceptions import HealthLinkError
from app.facilities.models import HealthcareFacility
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit
from app.visits.repository import (
    CurrentPatientContext,
    VisitsRepository,
)
from app.visits.schemas import (
    CitizenVisitSummary,
    DoctorCurrentPatientView,
    PatientSummary,
    VisitDraftUpdateRequest,
    VisitDraftView,
)


def _patient_summary(citizen: CitizenProfile) -> PatientSummary:
    user = citizen.user
    full_name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip() or user.email
    age_years: int | None = None
    dob_str: str | None = None
    if citizen.date_of_birth is not None:
        today = datetime.now(tz=timezone.utc).date()
        dob = citizen.date_of_birth
        years = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        age_years = max(years, 0)
        dob_str = dob.isoformat()
    return PatientSummary(
        citizen_id=citizen.id,
        full_name=full_name,
        date_of_birth=dob_str,
        gender=citizen.gender,
        blood_group=citizen.blood_group,
        age_years=age_years,
    )


def _visit_view_from_ctx(
    ctx: CurrentPatientContext,
    *,
    access_source: str,
) -> VisitDraftView:
    visit = ctx.visit
    return VisitDraftView(
        id=visit.id if visit is not None else uuid.UUID(int=0),
        citizen_id=ctx.citizen.id,
        doctor_role_registration_id=ctx.appointment.doctor_role_registration_id,
        facility_id=ctx.facility.id,
        appointment_id=ctx.appointment.id if visit is not None else None,
        visit_date=visit.visit_date if visit is not None else datetime.now(tz=timezone.utc),
        chief_complaint=visit.chief_complaint if visit is not None else None,
        clinical_notes=visit.clinical_notes if visit is not None else None,
        diagnosis=visit.diagnosis if visit is not None else None,
        follow_up_instructions=(
            visit.follow_up_instructions if visit is not None else None
        ),
        status=visit.status if visit is not None else "DRAFT",
        finalized_at=visit.finalized_at if visit is not None else None,
        updated_at=(
            visit.updated_at if visit is not None else datetime.now(tz=timezone.utc)
        ),
        patient=_patient_summary(ctx.citizen),
        access_source=access_source,
    )


def _current_patient_view(
    ctx: CurrentPatientContext,
    *,
    access_source: str,
) -> DoctorCurrentPatientView:
    return DoctorCurrentPatientView(
        queue_id=ctx.queue_entry.id,
        appointment_id=ctx.appointment.id,
        serial_number=ctx.appointment.serial_number,
        citizen_id=ctx.citizen.id,
        facility_id=ctx.facility.id,
        facility_name=ctx.facility.name,
        patient=_patient_summary(ctx.citizen),
        visit=(
            VisitDraftView.model_validate(_visit_view_from_ctx(ctx, access_source=access_source))
            if ctx.visit is not None
            else None
        ),
    )


class VisitsService:
    """Phase 12 consultation workspace business logic."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = VisitsRepository(db)

    # ------------------------------------------------------------------
    # Doctor workspace
    # ------------------------------------------------------------------

    def read_visit_for_doctor(
        self,
        acting_registration_id: uuid.UUID,
        visit_id: uuid.UUID,
    ) -> VisitDraftView:
        visit = self.db.get(MedicalVisit, visit_id)
        if visit is None:
            raise HealthLinkError(
                "Medical visit not found.", status_code=404
            )
        if visit.doctor_role_registration_id != acting_registration_id:
            raise HealthLinkError(
                "Only the authoring doctor may read this visit.",
                status_code=403,
            )
        ctx = self._rehydrate_context(visit)
        return VisitDraftView.model_validate(
            _visit_view_from_ctx(ctx, access_source="queue")
        )

    def get_current_patient_view(
        self, doctor_user_id: uuid.UUID
    ) -> DoctorCurrentPatientView:
        ctx = self.repository.load_current_patient_or_raise(doctor_user_id)
        return _current_patient_view(ctx, access_source="queue")

    def load_view_for_queue_entry(
        self, doctor_user_id: uuid.UUID, queue_id: uuid.UUID
    ) -> DoctorCurrentPatientView:
        ctx = self.repository.load_queue_entry_or_raise(doctor_user_id, queue_id)
        return _current_patient_view(ctx, access_source="queue")

    def start_visit_for_queue_entry(
        self, doctor_user_id: uuid.UUID, queue_id: uuid.UUID
    ) -> VisitDraftView:
        ctx = self.repository.load_queue_entry_or_raise(doctor_user_id, queue_id)
        if ctx.visit is not None:
            return VisitDraftView.model_validate(
                _visit_view_from_ctx(ctx, access_source="queue")
            )
        visit = self.repository.create_visit_for_appointment(
            citizen_id=ctx.citizen.id,
            doctor_role_registration_id=ctx.appointment.doctor_role_registration_id,
            facility_id=ctx.facility.id,
            appointment_id=ctx.appointment.id,
        )
        self.db.commit()
        self.db.refresh(visit)
        ctx = CurrentPatientContext(
            queue_entry=ctx.queue_entry,
            appointment=ctx.appointment,
            citizen=ctx.citizen,
            facility=ctx.facility,
            doctor_user=ctx.doctor_user,
            visit=visit,
        )
        return VisitDraftView.model_validate(
            _visit_view_from_ctx(ctx, access_source="queue")
        )

    def update_visit(
        self,
        *,
        visit_id: uuid.UUID,
        payload: VisitDraftUpdateRequest,
        acting_registration_id: uuid.UUID,
    ) -> VisitDraftView:
        visit = self.db.get(MedicalVisit, visit_id)
        if visit is None:
            raise HealthLinkError(
                "Medical visit not found.", status_code=404
            )
        if visit.doctor_role_registration_id != acting_registration_id:
            raise HealthLinkError(
                "Only the authoring doctor may edit this visit.",
                status_code=403,
            )
        if visit.status != "DRAFT":
            raise HealthLinkError(
                "Cannot edit a finalized visit.",
                status_code=409,
            )
        self.repository.update_visit_draft(
            visit,
            chief_complaint=payload.chief_complaint,
            clinical_notes=payload.clinical_notes,
            diagnosis=payload.diagnosis,
            follow_up_instructions=payload.follow_up_instructions,
        )
        self.db.commit()
        self.db.refresh(visit)

        ctx = self._rehydrate_context(visit)
        return VisitDraftView.model_validate(
            _visit_view_from_ctx(ctx, access_source="queue")
        )

    def _rehydrate_context(self, visit: MedicalVisit) -> CurrentPatientContext:
        from app.appointments.models import (
            AppointmentQueueEntry,
            DoctorPracticeSession,
        )

        citizen = self.db.get(CitizenProfile, visit.citizen_id)
        facility = self.db.get(HealthcareFacility, visit.facility_id)
        appointment = (
            self.db.get(Appointment, visit.appointment_id)
            if visit.appointment_id is not None
            else None
        )
        if (
            citizen is None
            or facility is None
            or appointment is None
        ):
            raise HealthLinkError(
                "Visit missing related rows.",
                status_code=500,
            )
        queue_entry = self.db.scalar(
            select(AppointmentQueueEntry)
            .join(
                DoctorPracticeSession,
                DoctorPracticeSession.id
                == AppointmentQueueEntry.practice_session_id,
            )
            .where(
                DoctorPracticeSession.doctor_role_registration_id
                == visit.doctor_role_registration_id
            )
            .order_by(AppointmentQueueEntry.became_current_at.desc())
            .limit(1)
        )
        registration = self.db.get(
            ProfessionalRoleRegistration, visit.doctor_role_registration_id
        )
        profile = (
            self.db.get(
                HealthcareProfessionalProfile, registration.professional_id
            )
            if registration is not None
            else None
        )
        doctor_user = (
            self.db.get(User, profile.user_id) if profile is not None else None
        )
        if (
            queue_entry is None
            or doctor_user is None
        ):
            raise HealthLinkError(
                "Visit missing related rows.",
                status_code=500,
            )
        return CurrentPatientContext(
            queue_entry=queue_entry,
            appointment=appointment,
            citizen=citizen,
            facility=facility,
            doctor_user=doctor_user,
            visit=visit,
        )

    # ------------------------------------------------------------------
    # Citizen read helpers
    # ------------------------------------------------------------------

    def read_visit_for_citizen(
        self,
        citizen_id: uuid.UUID,
        visit_id: uuid.UUID,
    ) -> VisitDraftView:
        visit = self.db.get(MedicalVisit, visit_id)
        if visit is None or visit.citizen_id != citizen_id:
            raise HealthLinkError(
                "Medical visit not found.", status_code=404
            )
        citizen = self.db.get(CitizenProfile, visit.citizen_id)
        facility = self.db.get(HealthcareFacility, visit.facility_id)
        appointment = (
            self.db.get(Appointment, visit.appointment_id)
            if visit.appointment_id is not None
            else None
        )
        if (
            citizen is None
            or facility is None
            or appointment is None
        ):
            raise HealthLinkError(
                "Visit missing related rows.", status_code=500
            )
        return VisitDraftView(
            id=visit.id,
            citizen_id=citizen.id,
            doctor_role_registration_id=visit.doctor_role_registration_id,
            facility_id=facility.id,
            appointment_id=appointment.id,
            visit_date=visit.visit_date,
            chief_complaint=visit.chief_complaint,
            clinical_notes=visit.clinical_notes,
            diagnosis=visit.diagnosis,
            follow_up_instructions=visit.follow_up_instructions,
            status=visit.status,
            finalized_at=visit.finalized_at,
            updated_at=visit.updated_at,
            patient=_patient_summary(citizen),
            access_source="citizen",
        )

    def list_citizen_visits(
        self,
        citizen_id: uuid.UUID,
        *,
        target_date: date | None = None,
    ) -> list[CitizenVisitSummary]:
        rows: Iterable = self.repository.list_visits_for_citizen(
            citizen_id, target_date=target_date
        )
        results: list[CitizenVisitSummary] = []
        for visit, appointment, doctor_user, facility in rows:
            results.append(
                CitizenVisitSummary(
                    id=visit.id,
                    doctor_user_id=doctor_user.id,
                    doctor_name=(
                        " ".join(
                            part
                            for part in (
                                doctor_user.first_name,
                                doctor_user.last_name,
                            )
                            if part
                        ).strip()
                        or doctor_user.email
                    ),
                    facility_id=facility.id,
                    facility_name=facility.name,
                    appointment_id=visit.appointment_id,
                    serial_number=appointment.serial_number if appointment else None,
                    visit_date=visit.visit_date,
                    status=visit.status,
                    finalized_at=visit.finalized_at,
                    chief_complaint=visit.chief_complaint,
                    diagnosis=visit.diagnosis,
                    follow_up_instructions=visit.follow_up_instructions,
                )
            )
        return results


__all__ = ["VisitsService"]
