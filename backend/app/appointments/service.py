from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    DoctorPracticeSession,
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
    ChamberAppointmentView,
    ChamberQueueActionResponse,
    ChamberSessionFinishResponse,
    ChamberSessionView,
)
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.doctors.models import PracticeWeekday
from app.facilities.models import HealthcareFacility
from app.professionals.dependencies import ProfessionalAuthContext


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


class ChamberSessionNotFoundError(HealthLinkError):
    def __init__(self, detail: str = "Chamber session not found") -> None:
        super().__init__(detail, status_code=404)


class ChamberQueueEntryNotFoundError(HealthLinkError):
    def __init__(self, detail: str = "Queue entry not found") -> None:
        super().__init__(detail, status_code=404)


class ChamberSessionStateError(HealthLinkError):
    """Raised when a chamber action is invalid for the session's current state."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class ChamberQueueStateError(HealthLinkError):
    """Raised when a queue entry's status forbids the requested action."""

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

        # Phase 13 exposes the prescription through the existing citizen
        # appointment history without creating a second, redundant history
        # endpoint. One query maps appointment -> visit -> prescription.
        from app.prescriptions.models import Prescription
        from app.visits.models import MedicalVisit

        appointment_ids = [row[0].id for row in rows]
        prescription_rows = self.db.execute(
            select(MedicalVisit.appointment_id, Prescription.id)
            .join(Prescription, Prescription.visit_id == MedicalVisit.id)
            .where(MedicalVisit.appointment_id.in_(appointment_ids))
        ).all()
        prescription_by_appointment = {
            appointment_id: prescription_id
            for appointment_id, prescription_id in prescription_rows
        }

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
                    prescription_id=prescription_by_appointment.get(
                        appointment.id
                    ),
                )
            )
        return AppointmentListResponse(appointments=entries)

    # ------------------------------------------------------------------
    # Phase 11 — chamber session + serial queue
    # ------------------------------------------------------------------

    @staticmethod
    def _serial_of(entry: AppointmentQueueEntry, appointment: Appointment) -> int:
        return appointment.serial_number

    def _queue_view(
        self, entry: AppointmentQueueEntry, appointment: Appointment
    ) -> ChamberAppointmentView:
        return ChamberAppointmentView(
            queue_id=entry.id,
            appointment_id=appointment.id,
            serial_number=appointment.serial_number,
            status=AppointmentStatus(appointment.status),
            queue_status=QueueStatus(entry.queue_status),
            reason=appointment.reason,
            booked_at=appointment.booked_at,
            became_current_at=entry.became_current_at,
            finished_at=entry.finished_at,
            removed_at=entry.removed_at,
        )

    def _next_waiting(self, session_id: uuid.UUID) -> AppointmentQueueEntry | None:
        """Centralized helper: pick the lowest WAITING serial in a session."""

        statement = (
            select(AppointmentQueueEntry)
            .join(
                Appointment,
                Appointment.id == AppointmentQueueEntry.appointment_id,
            )
            .where(
                AppointmentQueueEntry.practice_session_id == session_id,
                AppointmentQueueEntry.queue_status == QueueStatus.WAITING.value,
                Appointment.status == AppointmentStatus.BOOKED.value,
            )
            .order_by(Appointment.serial_number.asc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def start_session(
        self,
        context: ProfessionalAuthContext,
        *,
        facility_id: uuid.UUID,
        session_date: date,
    ) -> ChamberSessionView:
        registration = context.role_registration
        if registration.facility_id != facility_id:
            raise ChamberSessionStateError(
                "Verified doctor is not associated with this facility."
            )

        facility = self.repository.get_facility(facility_id)
        if facility is None or not facility.is_active:
            raise ChamberSessionNotFoundError("Facility not found.")

        self.repository._lock_for_queue(
            doctor_role_registration_id=registration.id,
            session_date=session_date,
        )

        session = self.repository.get_or_create_practice_session(
            doctor_role_registration_id=registration.id,
            facility_id=facility_id,
            appointment_date=session_date,
        )

        now = datetime.now(timezone.utc)
        if session.status == SessionStatus.NOT_STARTED.value:
            session.status = SessionStatus.ACTIVE.value
            session.started_at = now
            self.db.flush()

        if session.status == SessionStatus.COMPLETED.value:
            raise ChamberSessionStateError(
                "Chamber session is already closed for the day."
            )

        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ChamberSessionStateError(
                "Unable to start chamber session."
            ) from error

        self.db.refresh(session)

        # Immediately promote the lowest WAITING serial so the doctor has a
        # patient to work with the moment the session opens.
        promoted = self._promote_lowest_waiting(session.id)

        return self._build_session_view(session, facility, promoted)

    def view_today_queue(
        self,
        context: ProfessionalAuthContext,
        *,
        facility_id: uuid.UUID,
        session_date: date,
    ) -> ChamberSessionView | None:
        registration = context.role_registration
        if registration.facility_id != facility_id:
            raise ChamberSessionStateError(
                "Verified doctor is not associated with this facility."
            )
        facility = self.repository.get_facility(facility_id)
        if facility is None:
            raise ChamberSessionNotFoundError("Facility not found.")
        session = self.repository.get_practice_session_for_doctor(
            doctor_role_registration_id=registration.id,
            facility_id=facility_id,
            session_date=session_date,
        )
        if session is None:
            return None
        if session.status == SessionStatus.NOT_STARTED.value:
            return ChamberSessionView(
                id=session.id,
                facility_id=facility.id,
                facility_name=facility.name,
                session_date=session.session_date,
                status=SessionStatus(session.status),
                started_at=session.started_at,
                ended_at=session.ended_at,
                current=None,
                waiting=[],
                finished=[],
            )
        current = self.repository.current_queue_entry(session.id)
        return self._build_session_view(session, facility, current)

    def _build_session_view(
        self,
        session: DoctorPracticeSession,
        facility: HealthcareFacility,
        current: AppointmentQueueEntry | None,
    ) -> ChamberSessionView:
        entries = self.repository.list_queue_entries_for_session(session.id)
        appointments_by_id = self.repository.get_appointments_by_ids(
            [entry.appointment_id for entry in entries]
        )
        waiting: list[ChamberAppointmentView] = []
        finished: list[ChamberAppointmentView] = []
        terminal_statuses = {
            QueueStatus.DONE.value,
            QueueStatus.SKIPPED.value,
            QueueStatus.REMOVED.value,
        }
        for entry in entries:
            appointment = appointments_by_id.get(entry.appointment_id)
            if appointment is None:
                continue
            if appointment.status != AppointmentStatus.BOOKED.value:
                continue
            status_value = entry.queue_status
            if status_value == QueueStatus.WAITING.value:
                waiting.append(self._queue_view(entry, appointment))
            elif status_value in terminal_statuses:
                finished.append(self._queue_view(entry, appointment))
        return ChamberSessionView(
            id=session.id,
            facility_id=facility.id,
            facility_name=facility.name,
            session_date=session.session_date,
            status=SessionStatus(session.status),
            started_at=session.started_at,
            ended_at=session.ended_at,
            current=(
                self._queue_view(current, appointments_by_id[current.appointment_id])
                if current and current.appointment_id in appointments_by_id
                else None
            ),
            waiting=waiting,
            finished=finished,
        )

    def _promote_lowest_waiting(
        self, session_id: uuid.UUID
    ) -> AppointmentQueueEntry | None:
        """Atomically promote the lowest WAITING serial to CURRENT.

        Relies on the partial unique index on (practice_session_id) WHERE
        queue_status='CURRENT' to enforce that at most one CURRENT row
        exists per session.
        """

        next_entry = self._next_waiting(session_id)
        if next_entry is None:
            return None
        next_entry.queue_status = QueueStatus.CURRENT.value
        next_entry.became_current_at = datetime.now(timezone.utc)
        try:
            self.db.flush()
        except IntegrityError as error:
            self.db.rollback()
            raise ChamberQueueStateError(
                "Another patient is already in the chamber."
            ) from error
        return next_entry

    def call_next(
        self,
        context: ProfessionalAuthContext,
        *,
        facility_id: uuid.UUID,
        session_date: date,
    ) -> ChamberQueueActionResponse:
        registration = context.role_registration
        session = self._open_session(
            registration.id, facility_id, session_date
        )
        self.repository._lock_for_queue(
            doctor_role_registration_id=registration.id,
            session_date=session_date,
        )
        current = self.repository.current_queue_entry(session.id)
        if current is not None:
            raise ChamberQueueStateError(
                "A patient is already in the chamber. Complete or skip first."
            )
        promoted = self._promote_lowest_waiting(session.id)
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ChamberQueueStateError(
                "Unable to call next patient."
            ) from error
        if promoted is None:
            raise ChamberSessionStateError("No patients are waiting.")
        # Reload view from committed state.
        self.db.refresh(promoted)
        promoted_appointment = self.repository.get_appointment_by_id(
            promoted.appointment_id
        )
        return ChamberQueueActionResponse(
            queue_id=promoted.id,
            appointment_id=promoted.appointment_id,
            serial_number=self._serial_of(promoted, promoted_appointment),
            queue_status=QueueStatus(promoted.queue_status),
            appointment_status=AppointmentStatus(promoted_appointment.status),
            became_current_at=promoted.became_current_at,
            finished_at=None,
            removed_at=None,
            next_current=None,
        )

    def complete_current(
        self,
        context: ProfessionalAuthContext,
        queue_id: uuid.UUID,
    ) -> ChamberQueueActionResponse:
        return self._apply_queue_action(
            context,
            queue_id,
            target_status=QueueStatus.DONE,
            appointment_status=AppointmentStatus.COMPLETED,
            set_finished=True,
        )

    def skip_current(
        self,
        context: ProfessionalAuthContext,
        queue_id: uuid.UUID,
    ) -> ChamberQueueActionResponse:
        return self._apply_queue_action(
            context,
            queue_id,
            target_status=QueueStatus.SKIPPED,
            appointment_status=None,
            set_finished=True,
        )

    def remove_entry(
        self,
        context: ProfessionalAuthContext,
        queue_id: uuid.UUID,
    ) -> ChamberQueueActionResponse:
        return self._apply_queue_action(
            context,
            queue_id,
            target_status=QueueStatus.REMOVED,
            appointment_status=AppointmentStatus.REMOVED_BY_DOCTOR,
            set_removed=True,
        )

    def mark_no_show(
        self,
        context: ProfessionalAuthContext,
        queue_id: uuid.UUID,
    ) -> ChamberQueueActionResponse:
        # We don't have a dedicated NO_SHOW QueueStatus enum value in the
        # partial-unique-index path; reuse REMOVED for the queue side and
        # flip the appointment to NO_SHOW for the audit trail.
        return self._apply_queue_action(
            context,
            queue_id,
            target_status=QueueStatus.REMOVED,
            appointment_status=AppointmentStatus.NO_SHOW,
            set_removed=True,
        )

    def _apply_queue_action(
        self,
        context: ProfessionalAuthContext,
        queue_id: uuid.UUID,
        *,
        target_status: QueueStatus,
        appointment_status: AppointmentStatus | None,
        set_finished: bool = False,
        set_removed: bool = False,
    ) -> ChamberQueueActionResponse:
        registration = context.role_registration
        entry = self.repository.get_queue_entry_owned_by_doctor(
            queue_id=queue_id,
            doctor_role_registration_id=registration.id,
        )
        if entry is None:
            raise ChamberQueueEntryNotFoundError(
                "Queue entry not found for this doctor."
            )
        if entry.queue_status not in (
            QueueStatus.WAITING.value,
            QueueStatus.CURRENT.value,
        ):
            raise ChamberQueueStateError(
                "Queue entry is no longer in the active queue."
            )

        session = self.repository.get_practice_session_by_id(
            entry.practice_session_id
        )
        if session is None:
            raise ChamberQueueEntryNotFoundError(
                "Queue entry is not attached to an active session."
            )
        self.repository._lock_for_queue(
            doctor_role_registration_id=registration.id,
            session_date=session.session_date,
        )

        # If the entry we're acting on is CURRENT, the partial unique
        # index will free up the moment we flush; if it's WAITING, we
        # need to first vacate the CURRENT row before the next promote.
        current = self.repository.current_queue_entry(entry.practice_session_id)
        if (
            current is not None
            and current.id != entry.id
        ):
            raise ChamberQueueStateError(
                "Another patient is currently in the chamber."
            )

        appointment = self.repository.get_appointment_by_id(entry.appointment_id)
        if appointment is None:
            raise ChamberQueueEntryNotFoundError(
                "Appointment is no longer available."
            )

        now = datetime.now(timezone.utc)
        entry.queue_status = target_status.value
        if set_finished:
            entry.finished_at = now
        if set_removed:
            entry.removed_at = now
        if appointment_status is not None:
            appointment.status = appointment_status.value
            if appointment_status is AppointmentStatus.COMPLETED:
                appointment.completed_at = now
            self.db.flush()

        # After the action, auto-advance the next WAITING into CURRENT.
        promoted = self._promote_lowest_waiting(entry.practice_session_id)

        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ChamberQueueStateError(
                "Unable to apply queue action."
            ) from error

        self.db.refresh(entry)
        if promoted is not None:
            self.db.refresh(promoted)
        next_view = None
        if promoted is not None:
            promoted_appointment = self.repository.get_appointment_by_id(
                promoted.appointment_id
            )
            if promoted_appointment is not None:
                next_view = self._queue_view(promoted, promoted_appointment)
        return ChamberQueueActionResponse(
            queue_id=entry.id,
            appointment_id=entry.appointment_id,
            serial_number=self._serial_of(entry, appointment),
            queue_status=QueueStatus(entry.queue_status),
            appointment_status=AppointmentStatus(appointment.status),
            became_current_at=entry.became_current_at,
            finished_at=entry.finished_at,
            removed_at=entry.removed_at,
            next_current=next_view,
        )

    def finish_session(
        self,
        context: ProfessionalAuthContext,
        *,
        facility_id: uuid.UUID,
        session_date: date,
    ) -> ChamberSessionFinishResponse:
        registration = context.role_registration
        session = self.repository.get_practice_session_for_doctor(
            doctor_role_registration_id=registration.id,
            facility_id=facility_id,
            session_date=session_date,
        )
        if session is None:
            raise ChamberSessionNotFoundError(
                "No chamber session exists for this date."
            )
        if session.status == SessionStatus.COMPLETED.value:
            raise ChamberSessionStateError(
                "Chamber session is already closed for the day."
            )
        if session.status == SessionStatus.NOT_STARTED.value:
            raise ChamberSessionStateError(
                "Start the chamber session before finishing it."
            )

        self.repository._lock_for_queue(
            doctor_role_registration_id=registration.id,
            session_date=session_date,
        )

        session.status = SessionStatus.COMPLETED.value
        session.ended_at = datetime.now(timezone.utc)
        remaining_waiting = int(
            self.db.scalar(
                select(func.count(AppointmentQueueEntry.id)).where(
                    AppointmentQueueEntry.practice_session_id == session.id,
                    AppointmentQueueEntry.queue_status == QueueStatus.WAITING.value,
                )
            )
            or 0
        )
        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise ChamberSessionStateError(
                "Unable to finish chamber session."
            ) from error
        self.db.refresh(session)
        return ChamberSessionFinishResponse(
            id=session.id,
            facility_id=session.facility_id,
            session_date=session.session_date,
            status=SessionStatus(session.status),
            started_at=session.started_at,
            ended_at=session.ended_at,
            remaining_waiting=remaining_waiting,
        )

    def _open_session(
        self,
        doctor_role_registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        session_date: date,
    ) -> DoctorPracticeSession:
        session = self.repository.get_practice_session_for_doctor(
            doctor_role_registration_id=doctor_role_registration_id,
            facility_id=facility_id,
            session_date=session_date,
        )
        if session is None:
            raise ChamberSessionNotFoundError(
                "No chamber session exists for this date."
            )
        if session.status == SessionStatus.NOT_STARTED.value:
            raise ChamberSessionStateError(
                "Start the chamber session before queue actions."
            )
        if session.status == SessionStatus.COMPLETED.value:
            raise ChamberSessionStateError(
                "Chamber session is already closed for the day."
            )
        return session


__all__ = [
    "AppointmentService",
    "AppointmentValidationError",
    "AppointmentNotFoundError",
    "AppointmentScheduleUnavailableError",
    "AppointmentCapacityExceededError",
    "AppointmentBookingConflictError",
    "ChamberSessionNotFoundError",
    "ChamberQueueEntryNotFoundError",
    "ChamberSessionStateError",
    "ChamberQueueStateError",
]
