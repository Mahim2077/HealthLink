from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
from app.facilities.models import HealthcareFacility
from app.professionals.constants import (
    ProfessionalRoleCode,
    VerificationStatus,
)
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


class DoctorRepository:
    """Read + write helpers for doctor discovery and the doctor's own schedule.

    The repository is the single point that touches the database for the
    ``doctors`` package. Endpoints must never reach into SQLAlchemy directly.
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

    @staticmethod
    def _full_name_expr():
        return func.trim(
            func.lower(User.first_name + " " + User.last_name)
        )

    # ------------------------------------------------------------------
    # Citizen search
    # ------------------------------------------------------------------

    def search_verified_doctors(
        self,
        *,
        name: str | None,
        facility_name: str | None,
        weekday: str | None,
        limit: int,
    ) -> list[ProfessionalRoleRegistration]:
        """Return verified DOCTOR registrations matching the supplied filters.

        Filters are optional. ``weekday`` keeps only doctors that have at
        least one ACTIVE and non-deleted practice row for that weekday.
        """

        doctor_role_id = self._doctor_role_id()

        base = (
            select(ProfessionalRoleRegistration)
            .join(
                HealthcareProfessionalProfile,
                HealthcareProfessionalProfile.id
                == ProfessionalRoleRegistration.professional_id,
            )
            .join(User, User.id == HealthcareProfessionalProfile.user_id)
            .join(ProfessionalRole, ProfessionalRole.id == ProfessionalRoleRegistration.role_id)
            .where(
                ProfessionalRoleRegistration.role_id == doctor_role_id
            )
            .where(
                ProfessionalRoleRegistration.verification_status
                == VerificationStatus.VERIFIED.value
            )
            .where(ProfessionalRoleRegistration.facility_id.is_not(None))
            .options(
                selectinload(ProfessionalRoleRegistration.professional),
                selectinload(ProfessionalRoleRegistration.role),
                selectinload(ProfessionalRoleRegistration.facility),
            )
        )

        if name:
            like = f"%{name.lower()}%"
            base = base.where(self._full_name_expr().like(like))

        if facility_name:
            base = base.join(
                HealthcareFacility,
                HealthcareFacility.id == ProfessionalRoleRegistration.facility_id,
            ).where(func.lower(HealthcareFacility.name).like(f"%{facility_name.lower()}%"))

        if weekday:
            base = base.where(
                ProfessionalRoleRegistration.professional_id.in_(
                    select(HealthcareProfessionalProfile.id)
                    .join(
                        DoctorPracticeSchedule,
                        DoctorPracticeSchedule.doctor_user_id
                        == HealthcareProfessionalProfile.user_id,
                    )
                    .where(DoctorPracticeSchedule.weekday == weekday)
                    .where(DoctorPracticeSchedule.deleted_at.is_(None))
                    .where(
                        DoctorPracticeSchedule.status
                        == PracticeScheduleStatus.ACTIVE.value
                    )
                    .distinct()
                )
            )

        # Use plain columns in ORDER BY so PostgreSQL accepts the query
        # (it forbids ORDER BY expressions not present in SELECT when
        # combined with DISTINCT). SQLite happens to be tolerant of the
        # earlier expression-based ordering; the plain column order is
        # still deterministic and human-friendly.
        base = (
            base.order_by(
                User.first_name,
                User.last_name,
                ProfessionalRoleRegistration.id,
            )
            .limit(limit)
        )

        return list(self.db.scalars(base).unique())

    def get_verified_doctor_registration(
        self, doctor_user_id: uuid.UUID
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
                selectinload(ProfessionalRoleRegistration.professional),
                selectinload(ProfessionalRoleRegistration.role),
                selectinload(ProfessionalRoleRegistration.facility),
            )
        )
        return self.db.scalar(statement)

    def get_doctor_registration_detail(
        self, role_registration_id: uuid.UUID
    ) -> DoctorRegistrationDetail | None:
        return self.db.get(DoctorRegistrationDetail, role_registration_id)

    def get_user(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_facility(self, facility_id: uuid.UUID) -> HealthcareFacility | None:
        return self.db.get(HealthcareFacility, facility_id)

    # ------------------------------------------------------------------
    # Schedule CRUD (doctor self-management)
    # ------------------------------------------------------------------

    def list_schedules_for_doctor(
        self, doctor_user_id: uuid.UUID
    ) -> list[DoctorPracticeSchedule]:
        statement = (
            select(DoctorPracticeSchedule)
            .where(DoctorPracticeSchedule.doctor_user_id == doctor_user_id)
            .where(DoctorPracticeSchedule.deleted_at.is_(None))
            .options(selectinload(DoctorPracticeSchedule.facility))
            .order_by(
                DoctorPracticeSchedule.weekday,
                DoctorPracticeSchedule.start_time,
            )
        )
        return list(self.db.scalars(statement).unique())

    def list_active_schedules_for_doctor(
        self, doctor_user_id: uuid.UUID
    ) -> list[DoctorPracticeSchedule]:
        statement = (
            select(DoctorPracticeSchedule)
            .where(DoctorPracticeSchedule.doctor_user_id == doctor_user_id)
            .where(DoctorPracticeSchedule.deleted_at.is_(None))
            .where(
                DoctorPracticeSchedule.status == PracticeScheduleStatus.ACTIVE.value
            )
            .options(selectinload(DoctorPracticeSchedule.facility))
            .order_by(
                DoctorPracticeSchedule.weekday,
                DoctorPracticeSchedule.start_time,
            )
        )
        return list(self.db.scalars(statement).unique())

    def list_schedules_for_doctor_facility_weekday(
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
            )
        )
        return list(self.db.scalars(statement))

    def get_schedule(self, schedule_id: uuid.UUID) -> DoctorPracticeSchedule | None:
        return self.db.get(DoctorPracticeSchedule, schedule_id)

    def add(self, instance: object) -> object:
        self.db.add(instance)
        return instance

    def delete(self, instance: object) -> None:
        self.db.delete(instance)

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, instance: object) -> None:
        self.db.refresh(instance)
