from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.doctors.models import DoctorPracticeSchedule
from app.doctors.repository import DoctorRepository
from app.doctors.schemas import (
    DoctorProfile,
    DoctorSummary,
    PracticeDay,
    PracticeScheduleEntry,
    PracticeScheduleWriteRequest,
)


class DoctorNotFoundError(HealthLinkError):
    def __init__(self, detail: str = "Doctor not found") -> None:
        super().__init__(detail, status_code=404)


class DoctorScheduleConflictError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class DoctorScheduleValidationError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=400)


@dataclass(frozen=True)
class DoctorScheduleMutationResult:
    schedule: PracticeScheduleEntry
    is_new: bool


class DoctorService:
    """Service layer orchestrating doctor discovery and schedule CRUD."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = DoctorRepository(db)

    # ------------------------------------------------------------------
    # Discovery (citizen-facing)
    # ------------------------------------------------------------------

    def search_doctors(
        self,
        *,
        name: str | None,
        facility_name: str | None,
        weekday: str | None,
        limit: int,
    ) -> list[DoctorSummary]:
        registrations = self.repository.search_verified_doctors(
            name=name,
            facility_name=facility_name,
            weekday=weekday,
            limit=limit,
        )
        return [_to_summary(registration) for registration in registrations]

    def get_doctor_profile(self, doctor_user_id: uuid.UUID) -> DoctorProfile:
        registration = self.repository.get_verified_doctor_registration(doctor_user_id)
        if registration is None:
            raise DoctorNotFoundError()
        detail = self.repository.get_doctor_registration_detail(registration.id)
        practice_schedules = self.repository.list_active_schedules_for_doctor(
            doctor_user_id
        )
        practice_days = [_to_practice_day(schedule) for schedule in practice_schedules]
        return _to_profile(registration, detail, practice_days)

    def get_doctor_practice_days(
        self, doctor_user_id: uuid.UUID
    ) -> list[PracticeDay]:
        registration = self.repository.get_verified_doctor_registration(doctor_user_id)
        if registration is None:
            raise DoctorNotFoundError()
        schedules = self.repository.list_active_schedules_for_doctor(doctor_user_id)
        return [_to_practice_day(schedule) for schedule in schedules]

    # ------------------------------------------------------------------
    # Schedule self-management (verified DOCTOR)
    # ------------------------------------------------------------------

    def list_schedule_entries(
        self, doctor_user_id: uuid.UUID
    ) -> list[PracticeScheduleEntry]:
        schedules = self.repository.list_schedules_for_doctor(doctor_user_id)
        return [_to_schedule_entry(schedule) for schedule in schedules]

    def create_schedule_entry(
        self,
        doctor_user_id: uuid.UUID,
        request: PracticeScheduleWriteRequest,
    ) -> DoctorScheduleMutationResult:
        return self._upsert_schedule_entry(
            doctor_user_id=doctor_user_id,
            request=request,
            existing=None,
            is_new=True,
        )

    def update_schedule_entry(
        self,
        doctor_user_id: uuid.UUID,
        schedule_id: uuid.UUID,
        request: PracticeScheduleWriteRequest,
    ) -> DoctorScheduleMutationResult:
        existing = self.repository.get_schedule(schedule_id)
        if existing is None or existing.deleted_at is not None:
            raise DoctorNotFoundError("Practice schedule not found.")
        if existing.doctor_user_id != doctor_user_id:
            raise DoctorNotFoundError("Practice schedule not found.")
        return self._upsert_schedule_entry(
            doctor_user_id=doctor_user_id,
            request=request,
            existing=existing,
            is_new=False,
        )

    def delete_schedule_entry(
        self, doctor_user_id: uuid.UUID, schedule_id: uuid.UUID
    ) -> uuid.UUID:
        existing = self.repository.get_schedule(schedule_id)
        if existing is None or existing.deleted_at is not None:
            raise DoctorNotFoundError("Practice schedule not found.")
        if existing.doctor_user_id != doctor_user_id:
            raise DoctorNotFoundError("Practice schedule not found.")
        existing.deleted_at = _now()
        try:
            self.repository.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise DoctorScheduleConflictError(
                "Practice schedule could not be deleted."
            ) from error
        return existing.id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _upsert_schedule_entry(
        self,
        *,
        doctor_user_id: uuid.UUID,
        request: PracticeScheduleWriteRequest,
        existing: DoctorPracticeSchedule | None,
        is_new: bool,
    ) -> DoctorScheduleMutationResult:
        facility = self.repository.get_facility(request.facility_id)
        if facility is None or not facility.is_active:
            raise DoctorScheduleValidationError(
                "Facility is not available for scheduling."
            )

        registration = self.repository.get_verified_doctor_registration(doctor_user_id)
        if registration is None:
            raise DoctorScheduleValidationError(
                "Only verified doctors may manage practice schedules."
            )

        weekday = request.weekday.value
        start_time = request.start_time
        end_time = request.end_time

        if start_time >= end_time:
            raise DoctorScheduleValidationError(
                "Practice end time must be after start time."
            )

        overlapping = self._find_overlap(
            doctor_user_id=doctor_user_id,
            facility_id=request.facility_id,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            ignore_id=existing.id if existing else None,
        )
        if overlapping:
            raise DoctorScheduleConflictError(
                "A practice schedule already exists for this window."
            )

        status = request.status.value

        if existing is None:
            instance = DoctorPracticeSchedule(
                doctor_user_id=doctor_user_id,
                facility_id=request.facility_id,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                max_patients=request.max_patients,
                status=status,
            )
            self.repository.add(instance)
        else:
            existing.facility_id = request.facility_id
            existing.weekday = weekday
            existing.start_time = start_time
            existing.end_time = end_time
            existing.max_patients = request.max_patients
            existing.status = status
            existing.deleted_at = None
            instance = existing

        try:
            self.repository.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise DoctorScheduleConflictError(
                "Practice schedule could not be saved."
            ) from error

        self.db.expire_all()
        refreshed = self.repository.list_schedules_for_doctor(doctor_user_id)
        matched = next(
            (row for row in refreshed if row.id == instance.id),
            None,
        )
        if matched is None:
            # Defensive: schedule must exist after commit.
            raise DoctorNotFoundError("Practice schedule not found after save.")
        entry = _to_schedule_entry(matched)
        return DoctorScheduleMutationResult(schedule=entry, is_new=is_new)

    def _find_overlap(
        self,
        *,
        doctor_user_id: uuid.UUID,
        facility_id: uuid.UUID,
        weekday: str,
        start_time,
        end_time,
        ignore_id: uuid.UUID | None,
    ) -> list[DoctorPracticeSchedule]:
        existing = self.repository.list_schedules_for_doctor_facility_weekday(
            doctor_user_id=doctor_user_id,
            facility_id=facility_id,
            weekday=weekday,
        )
        candidates = [
            item
            for item in existing
            if ignore_id is None or item.id != ignore_id
        ]
        return [
            item
            for item in candidates
            if item.start_time < end_time and start_time < item.end_time
        ]


# ----------------------------------------------------------------------
# Helpers / DTO construction
# ----------------------------------------------------------------------


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _to_summary(registration) -> DoctorSummary:
    profile = registration.professional
    user = _profile_user(profile)
    facility = registration.facility
    role = registration.role
    return DoctorSummary(
        id=profile.user_id,
        name=f"{user.first_name} {user.last_name}".strip(),
        first_name=user.first_name,
        last_name=user.last_name,
        facility_id=facility.id,
        facility_name=facility.name,
        facility_type=facility.facility_type,
        designation=registration.designation,
        role_code=role.code,
        verified=registration.verification_status == "VERIFIED",
        specialization=role.name,
    )


def _to_profile(registration, detail, practice_days: list[PracticeDay]) -> DoctorProfile:
    summary = _to_summary(registration)
    profile = registration.professional
    user = _profile_user(profile)
    return DoctorProfile(
        **summary.model_dump(),
        email=user.email,
        bmdc_number=detail.bmdc_registration_number if detail else None,
        verified_at=registration.verified_at,
        submitted_at=registration.submitted_at,
        practice_days=practice_days,
    )


def _to_practice_day(schedule: DoctorPracticeSchedule) -> PracticeDay:
    facility = schedule.facility
    return PracticeDay(
        id=schedule.id,
        facility_id=schedule.facility_id,
        facility_name=facility.name if facility else "",
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        max_patients=schedule.max_patients,
        status=schedule.status,
    )


def _to_schedule_entry(schedule: DoctorPracticeSchedule) -> PracticeScheduleEntry:
    facility = schedule.facility
    return PracticeScheduleEntry(
        id=schedule.id,
        facility_id=schedule.facility_id,
        facility_name=facility.name if facility else "",
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        max_patients=schedule.max_patients,
        status=schedule.status,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def _profile_user(profile):
    return profile.user