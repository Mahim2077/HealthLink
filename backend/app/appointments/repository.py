from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    DoctorPracticeSession,
    QueueStatus,
    SessionStatus,
)
from app.auth.models import User
from app.citizens.models import CitizenProfile
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
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


@dataclass(frozen=True)
class AppointmentFinishContext:
    """Rows that participate in the Phase 14 finish transaction."""

    appointment: Appointment
    queue_entry: AppointmentQueueEntry
    practice_session: DoctorPracticeSession


class AppointmentBookingConflictError(Exception):
    """Raised when the database uniquely guards a duplicate serial."""


class AppointmentRepository:
    """Read + write helpers for appointment booking and history.

    All SQLAlchemy access for the ``appointments`` package goes through
    this class. Methods that participate in booking acquire a
    transaction-scoped PostgreSQL advisory lock when the dialect supports
    it, falling back to SELECT-only inside an explicit transaction for
    SQLite (used by the unit suite).
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
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

    def _lock_for_booking(
        self,
        doctor_role_registration_id: uuid.UUID,
        appointment_date: date,
    ) -> None:
        """Acquire a transaction-scoped advisory lock keyed by doctor+date.

        Computes a stable bigint key by xor-ing the UUID halves together
        and folding with the date ordinal. Pure-Python so it works against
        both PostgreSQL (where it's an actual lock) and SQLite (where the
        call is a no-op — SQLite serializes writes via its own locks).
        """

        bind = self.db.get_bind()
        if bind.dialect.name != "postgresql":
            return
        u = int(doctor_role_registration_id.int)
        key = (u ^ (u >> 32)) & 0x7FFFFFFFFFFFFFFF
        key = key ^ date.toordinal(appointment_date)
        self.db.execute(
            select(func.pg_advisory_xact_lock(key))
        ).scalar()

    # ------------------------------------------------------------------
    # Booking support
    # ------------------------------------------------------------------

    def get_verified_doctor_registration_by_user_id(
        self,
        doctor_user_id: uuid.UUID,
    ) -> ProfessionalRoleRegistration | None:
        doctor_role_id = self._doctor_role_id()
        statement = (
            select(ProfessionalRoleRegistration)
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .where(HealthcareProfessionalProfile.user_id == doctor_user_id)
            .where(ProfessionalRoleRegistration.role_id == doctor_role_id)
            .where(
                ProfessionalRoleRegistration.verification_status
                == VerificationStatus.VERIFIED.value
            )
            .options(
                selectinload(ProfessionalRoleRegistration.role),
                selectinload(ProfessionalRoleRegistration.facility),
            )
        )
        return self.db.scalar(statement)

    def get_citizen_profile_by_user_id(
        self, citizen_user_id: uuid.UUID
    ) -> CitizenProfile | None:
        return self.db.scalar(
            select(CitizenProfile).where(CitizenProfile.user_id == citizen_user_id)
        )

    def get_facility(self, facility_id: uuid.UUID) -> HealthcareFacility | None:
        return self.db.get(HealthcareFacility, facility_id)

    def list_active_schedules_for_doctor_on_weekday(
        self,
        doctor_user_id: uuid.UUID,
        facility_id: uuid.UUID,
        weekday: str,
    ) -> list[DoctorPracticeSchedule]:
        statement = select(DoctorPracticeSchedule).where(
            and_(
                DoctorPracticeSchedule.doctor_user_id == doctor_user_id,
                DoctorPracticeSchedule.facility_id == facility_id,
                DoctorPracticeSchedule.weekday == weekday,
                DoctorPracticeSchedule.deleted_at.is_(None),
                DoctorPracticeSchedule.status
                == PracticeScheduleStatus.ACTIVE.value,
            )
        )
        return list(self.db.scalars(statement))

    def count_active_appointments_for_day(
        self,
        doctor_role_registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        appointment_date: date,
    ) -> int:
        active_states = (AppointmentStatus.BOOKED.value,)
        statement = select(func.count(Appointment.id)).where(
            Appointment.doctor_role_registration_id == doctor_role_registration_id,
            Appointment.facility_id == facility_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(active_states),
        )
        return int(self.db.scalar(statement) or 0)

    def max_serial_for_day(
        self,
        doctor_role_registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        appointment_date: date,
    ) -> int:
        statement = select(func.max(Appointment.serial_number)).where(
            Appointment.doctor_role_registration_id == doctor_role_registration_id,
            Appointment.facility_id == facility_id,
            Appointment.appointment_date == appointment_date,
        )
        return int(self.db.scalar(statement) or 0)

    def get_or_create_practice_session(
        self,
        doctor_role_registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        appointment_date: date,
    ) -> DoctorPracticeSession:
        """Lookup-or-create today's practice session.

        Uses a SELECT-then-INSERT race-tolerant pattern: an IntegrityError
        from the unique key is recovered by re-selecting. Caller must be
        inside the same transaction as the insert.
        """

        from sqlalchemy.exc import IntegrityError

        session = self.db.scalar(
            select(DoctorPracticeSession).where(
                DoctorPracticeSession.doctor_role_registration_id
                == doctor_role_registration_id,
                DoctorPracticeSession.facility_id == facility_id,
                DoctorPracticeSession.session_date == appointment_date,
            )
        )
        if session is not None:
            return session
        session = DoctorPracticeSession(
            doctor_role_registration_id=doctor_role_registration_id,
            facility_id=facility_id,
            session_date=appointment_date,
            status=SessionStatus.NOT_STARTED.value,
        )
        self.db.add(session)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            session = self.db.scalar(
                select(DoctorPracticeSession).where(
                    DoctorPracticeSession.doctor_role_registration_id
                    == doctor_role_registration_id,
                    DoctorPracticeSession.facility_id == facility_id,
                    DoctorPracticeSession.session_date == appointment_date,
                )
            )
            if session is None:
                raise
        return session

    def add_appointment(self, appointment: Appointment) -> None:
        self.db.add(appointment)

    def add_queue_entry(self, entry: AppointmentQueueEntry) -> None:
        self.db.add(entry)

    def get_appointments_by_ids(
        self, appointment_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, Appointment]:
        """Fetch appointments by ID in a single SELECT; returns a dict."""

        if not appointment_ids:
            return {}
        statement = select(Appointment).where(Appointment.id.in_(appointment_ids))
        return {appointment.id: appointment for appointment in self.db.scalars(statement)}

    def get_appointment_by_id(self, appointment_id: uuid.UUID) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def get_practice_session_by_id(
        self, session_id: uuid.UUID
    ) -> DoctorPracticeSession | None:
        return self.db.get(DoctorPracticeSession, session_id)

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def list_appointments_for_citizen(
        self, citizen_id: uuid.UUID
    ) -> Sequence:
        """List appointments for one citizen alongside the doctor's
        professional role registration (used for doctor name + facility).
        """

        statement = (
            select(Appointment, ProfessionalRoleRegistration)
            .join(
                ProfessionalRoleRegistration,
                ProfessionalRoleRegistration.id
                == Appointment.doctor_role_registration_id,
            )
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .where(Appointment.citizen_id == citizen_id)
            .order_by(
                Appointment.appointment_date.desc(),
                Appointment.serial_number.asc(),
            )
        )
        return list(self.db.execute(statement).all())

    def list_users_by_id(
        self, user_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, User]:
        if not user_ids:
            return {}
        rows = self.db.scalars(
            select(User).where(User.id.in_(list(user_ids)))
        ).unique()
        return {row.id: row for row in rows}

    # ------------------------------------------------------------------
    # Phase 11 — chamber session + serial queue
    # ------------------------------------------------------------------

    def _lock_for_queue(
        self,
        doctor_role_registration_id: uuid.UUID,
        session_date: date,
    ) -> None:
        """Transaction-scoped advisory lock for chamber queue mutations.

        Mirrors ``_lock_for_booking`` but uses a different folded key so
        booking locks and queue locks do not collide when a doctor is
        racing a late-arriving booking while running the queue.
        """

        bind = self.db.get_bind()
        if bind.dialect.name != "postgresql":
            return
        u = int(doctor_role_registration_id.int)
        key = (u ^ (u >> 32)) & 0x7FFFFFFFFFFFFFFF
        key = key ^ (date.toordinal(session_date) << 1) ^ 0x5A5A5A5A
        self.db.execute(
            select(func.pg_advisory_xact_lock(key))
        ).scalar()

    def get_practice_session_for_doctor(
        self,
        *,
        doctor_role_registration_id: uuid.UUID,
        facility_id: uuid.UUID,
        session_date: date,
    ) -> DoctorPracticeSession | None:
        return self.db.scalar(
            select(DoctorPracticeSession).where(
                DoctorPracticeSession.doctor_role_registration_id
                == doctor_role_registration_id,
                DoctorPracticeSession.facility_id == facility_id,
                DoctorPracticeSession.session_date == session_date,
            )
        )

    def list_queue_entries_for_session(
        self, session_id: uuid.UUID
    ) -> Sequence[AppointmentQueueEntry]:
        statement = (
            select(AppointmentQueueEntry)
            .join(
                Appointment,
                Appointment.id == AppointmentQueueEntry.appointment_id,
            )
            .where(AppointmentQueueEntry.practice_session_id == session_id)
            .order_by(Appointment.serial_number.asc())
        )
        return list(self.db.scalars(statement))

    def current_queue_entry(
        self, session_id: uuid.UUID
    ) -> AppointmentQueueEntry | None:
        return self.db.scalar(
            select(AppointmentQueueEntry).where(
                AppointmentQueueEntry.practice_session_id == session_id,
                AppointmentQueueEntry.queue_status == QueueStatus.CURRENT.value,
            )
        )

    def get_queue_entry_owned_by_doctor(
        self,
        *,
        queue_id: uuid.UUID,
        doctor_role_registration_id: uuid.UUID,
    ) -> AppointmentQueueEntry | None:
        """Return the queue entry only if it belongs to the doctor's session."""

        statement = (
            select(AppointmentQueueEntry)
            .join(
                DoctorPracticeSession,
                DoctorPracticeSession.id
                == AppointmentQueueEntry.practice_session_id,
            )
            .where(
                AppointmentQueueEntry.id == queue_id,
                DoctorPracticeSession.doctor_role_registration_id
                == doctor_role_registration_id,
            )
            .options()
        )
        return self.db.scalar(statement)

    def get_appointment_finish_context(
        self,
        *,
        appointment_id: uuid.UUID,
        doctor_role_registration_id: uuid.UUID,
        for_update: bool = False,
    ) -> AppointmentFinishContext | None:
        """Load an appointment only when the active doctor owns its queue.

        ``FOR UPDATE`` is used after the queue advisory lock is acquired so a
        concurrent retry observes either the complete pre-finish state or the
        complete post-finish state, never a partial transition.
        """

        statement = (
            select(
                Appointment,
                AppointmentQueueEntry,
                DoctorPracticeSession,
            )
            .join(
                AppointmentQueueEntry,
                AppointmentQueueEntry.appointment_id == Appointment.id,
            )
            .join(
                DoctorPracticeSession,
                DoctorPracticeSession.id
                == AppointmentQueueEntry.practice_session_id,
            )
            .where(
                Appointment.id == appointment_id,
                Appointment.doctor_role_registration_id
                == doctor_role_registration_id,
                DoctorPracticeSession.doctor_role_registration_id
                == doctor_role_registration_id,
            )
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        row = self.db.execute(statement).one_or_none()
        if row is None:
            return None
        return AppointmentFinishContext(
            appointment=row[0],
            queue_entry=row[1],
            practice_session=row[2],
        )


__all__ = [
    "AppointmentFinishContext",
    "AppointmentRepository",
    "AppointmentBookingConflictError",
]
