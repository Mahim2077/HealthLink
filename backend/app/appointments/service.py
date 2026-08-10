from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    QueueStatus,
    SessionStatus,
)
from app.appointments.repository import AppointmentRepository
from app.appointments.schemas import (
    AppointmentBookingRequest,
    AppointmentBookingResponse,
    AppointmentListEntry,
    AppointmentListResponse,
    AppointmentQueueEntryView,
)
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.doctors.models import PracticeWeekday


class AppointmentValidationError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=400)


class AppointmentNotFoundError(HealthLinkError):
    def __init__(self, detail: str = "Appointment not found") -> None:
        super().__init__(detail, status_code=404)


class AppointmentScheduleUnavailableError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class AppointmentCapacityExceededError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class AppointmentBookingConflictError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


@dataclass(frozen=True)
class BookedAppointment:
    appointment: Appointment
    queue_entry: AppointmentQueueEntry
    facility_name: str
    doctor_user_id: uuid.UUID


class AppointmentService:
    """Service layer for Phase 10 citizen-facing appointment booking and history.

    Implements the transaction flow described in V6 section 17:

        BEGIN
            acquire transaction-scoped advisory lock
            load applicable practice schedule
            count active appointments
            verify active_count < max_patients
            read MAX(serial_number)
            create appointment
            get/create daily practice session
            create queue entry
        COMMIT
    """

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = AppointmentRepository(db)

    # ------------------------------------------------------------------
    # Booking
    # ------------------------------------------------------------------

    def book_appointment(
        self,
        citizen_user_id: uuid.UUID,
        request: AppointmentBookingRequest,
    ) -> AppointmentBookingResponse:
        citizen = self.repository.get_citizen_profile_by_user_id(citizen_user_id)
        if citizen is None:
            raise AppointmentValidationError("Citizen profile required.")

        registration = self.repository.get_verified_doctor_registration_by_user_id(
            request.doctor_user_id,
        )
        if registration is None:
            raise AppointmentNotFoundError("Doctor is not available for booking.")

        facility = self.repository.get_facility(request.facility_id)
        if facility is None or not facility.is_active:
            raise AppointmentValidationError(
                "Facility is not available for booking."
            )

        weekday_name = request.appointment_date.strftime("%A").upper()
        try:
            weekday = PracticeWeekday(weekday_name)
        except ValueError as error:
            raise AppointmentValidationError(
                "Unable to derive weekday from appointment_date."
            ) from error

        schedules = self.repository.list_active_schedules_for_doctor_on_weekday(
            doctor_user_id=request.doctor_user_id,
            facility_id=request.facility_id,
            weekday=weekday.value,
        )
        if not schedules:
            raise AppointmentScheduleUnavailableError(
                "Doctor does not have an active practice schedule for "
                f"{weekday.value} at this facility."
            )

        # Capacity is capped at the largest schedule window for the day so
        # back-to-back half-day chambers don't unfairly reject bookings.
        max_capacity = max(schedule.max_patients for schedule in schedules)

        # Acquire the transaction-scoped advisory lock AFTER the read-only
        # preflight so we don't needlessly hold the lock on bad payloads.
        self.repository._lock_for_booking(
            doctor_role_registration_id=registration.id,
            appointment_date=request.appointment_date,
        )

        active_count = self.repository.count_active_appointments_for_day(
            doctor_role_registration_id=registration.id,
            facility_id=request.facility_id,
            appointment_date=request.appointment_date,
        )
        if active_count >= max_capacity:
            raise AppointmentCapacityExceededError(
                "Doctor has no remaining capacity for this date."
            )

        next_serial = self.repository.max_serial_for_day(
            doctor_role_registration_id=registration.id,
            facility_id=request.facility_id,
            appointment_date=request.appointment_date,
        ) + 1

        now = datetime.now(timezone.utc)
        appointment = Appointment(
            citizen_id=citizen.id,
            doctor_role_registration_id=registration.id,
            facility_id=request.facility_id,
            appointment_date=request.appointment_date,
            serial_number=next_serial,
            status=AppointmentStatus.BOOKED.value,
            reason=request.reason,
            booked_at=now,
        )
        self.repository.add_appointment(appointment)

        try:
            self.db.flush()
        except IntegrityError as error:
            self.db.rollback()
            raise AppointmentBookingConflictError(
                "Serial number collision — please retry."
            ) from error

        session = self.repository.get_or_create_practice_session(
            doctor_role_registration_id=registration.id,
            facility_id=request.facility_id,
            appointment_date=request.appointment_date,
        )

        queue_entry = AppointmentQueueEntry(
            appointment_id=appointment.id,
            practice_session_id=session.id,
            queue_status=QueueStatus.WAITING.value,
        )
        self.repository.add_queue_entry(queue_entry)

        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise AppointmentBookingConflictError(
                "Appointment could not be saved — please retry."
            ) from error

        self.db.refresh(appointment)
        self.db.refresh(queue_entry)

        return AppointmentBookingResponse(
            id=appointment.id,
            citizen_id=appointment.citizen_id,
            doctor_role_registration_id=appointment.doctor_role_registration_id,
            doctor_user_id=request.doctor_user_id,
            facility_id=appointment.facility_id,
            facility_name=facility.name,
            appointment_date=appointment.appointment_date,
            serial_number=appointment.serial_number,
            status=AppointmentStatus(appointment.status),
            reason=appointment.reason,
            booked_at=appointment.booked_at,
            queue=AppointmentQueueEntryView(
                id=queue_entry.id,
                queue_status=QueueStatus(queue_entry.queue_status),
                became_current_at=queue_entry.became_current_at,
                finished_at=queue_entry.finished_at,
                removed_at=queue_entry.removed_at,
            ),
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def list_my_appointments(
        self, citizen_user_id: uuid.UUID
    ) -> AppointmentListResponse:
        citizen = self.repository.get_citizen_profile_by_user_id(citizen_user_id)
        if citizen is None:
            raise AppointmentValidationError("Citizen profile required.")

        rows = self.repository.list_appointments_for_citizen(citizen.id)
        if not rows:
            return AppointmentListResponse(appointments=[])

        professional_ids = list({row[1].professional_id for row in rows})
        prof_to_user: dict[uuid.UUID, uuid.UUID] = {}
        if professional_ids:
            from app.professionals.models import HealthcareProfessionalProfile

            profile_rows = self.db.execute(
                select(
                    HealthcareProfessionalProfile.id,
                    HealthcareProfessionalProfile.user_id,
                ).where(HealthcareProfessionalProfile.id.in_(professional_ids))
            ).all()
            prof_to_user = {row[0]: row[1] for row in profile_rows}

        user_ids = list({user_id for user_id in prof_to_user.values()})
        users_by_id = self.repository.list_users_by_id(user_ids)

        entries: list[AppointmentListEntry] = []
        for appointment, registration in rows:
            user_id = prof_to_user.get(registration.professional_id)
            user = users_by_id.get(user_id) if user_id else None
            full_name = (
                f"{user.first_name} {user.last_name}".strip()
                if user is not None
                else ""
            )
            entries.append(
                AppointmentListEntry(
                    id=appointment.id,
                    doctor_user_id=user_id,
                    doctor_name=full_name,
                    facility_id=appointment.facility_id,
                    facility_name=registration.facility_name_submitted or "",
                    appointment_date=appointment.appointment_date,
                    serial_number=appointment.serial_number,
                    status=AppointmentStatus(appointment.status),
                    booked_at=appointment.booked_at,
                    cancelled_at=appointment.cancelled_at,
                    completed_at=appointment.completed_at,
                )
            )
        return AppointmentListResponse(appointments=entries)


__all__ = [
    "AppointmentService",
    "AppointmentValidationError",
    "AppointmentNotFoundError",
    "AppointmentScheduleUnavailableError",
    "AppointmentCapacityExceededError",
    "AppointmentBookingConflictError",
]
