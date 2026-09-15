from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.doctors.models import DoctorPracticeSchedule
from app.doctors.repository import DoctorRepository
from app.doctors.schemas import (
    DoctorFacilityOption,
    DoctorProfile,
    DoctorSearchResponse,
    DoctorSort,
    DoctorSummary,
    NextPracticeWindow,
    PracticeDay,
    PracticeScheduleEntry,
    PracticeScheduleWriteRequest,
)
from app.doctors.facility_choice_schemas import DoctorFacilityChoice
from app.locations.service import BangladeshAreaNotFoundError, resolve_area
from app.professionals.constants import (
    DOCTOR_SPECIALIZATION_LABELS,
    DoctorSpecialization,
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
        query: str | None = None,
        specialization: str | None = None,
        facility_id: uuid.UUID | None = None,
        weekday: str | None,
        sort: DoctorSort = DoctorSort.BEST_MATCH,
        latitude: float | None = None,
        longitude: float | None = None,
        district_code: str | None = None,
        upazila_code: str | None = None,
        offset: int = 0,
        limit: int,
    ) -> DoctorSearchResponse:
        registrations = self.repository.search_verified_doctors(
            name=name,
            facility_name=facility_name,
            query=query,
            specialization=specialization,
            facility_id=facility_id,
            weekday=weekday,
            offset=0,
            limit=500,
        )
        details = self.repository.get_doctor_registration_details(
            [registration.id for registration in registrations]
        )
        doctor_ids = [registration.professional.user_id for registration in registrations]
        schedules = self.repository.list_active_schedules_for_doctors(doctor_ids)
        schedule_map: dict[uuid.UUID, list[DoctorPracticeSchedule]] = {}
        for schedule in schedules:
            schedule_map.setdefault(schedule.doctor_user_id, []).append(schedule)

        origin: tuple[float, float] | None = None
        location_is_manual = district_code is not None and upazila_code is not None
        if latitude is not None and longitude is not None:
            origin = (latitude, longitude)
        elif location_is_manual:
            _, upazila = resolve_area(district_code, upazila_code)
            origin = (upazila.point.latitude, upazila.point.longitude)

        summaries: list[DoctorSummary] = []
        for registration in registrations:
            facility = registration.facility
            distance = None
            if origin is not None:
                if (
                    facility.location_status != "CONFIRMED"
                    or facility.latitude is None
                    or facility.longitude is None
                ):
                    continue
                distance = _distance_km(
                    origin[0], origin[1], facility.latitude, facility.longitude
                )
                if location_is_manual and distance > 50:
                    continue
            doctor_id = registration.professional.user_id
            next_practice = _next_practice(schedule_map.get(doctor_id, []))
            summaries.append(
                _to_summary(
                    registration,
                    details.get(registration.id),
                    next_practice=next_practice,
                    distance_km=round(distance, 1) if distance is not None else None,
                )
            )

        if sort is DoctorSort.NEAREST:
            summaries.sort(key=lambda row: row.distance_km if row.distance_km is not None else float("inf"))
        elif sort is DoctorSort.EARLIEST_PRACTICE:
            summaries.sort(key=_practice_sort_key)
        elif sort is DoctorSort.FACILITY_NAME:
            summaries.sort(key=lambda row: (row.facility_name.lower(), row.name.lower()))
        elif sort is DoctorSort.DOCTOR_NAME:
            summaries.sort(key=lambda row: row.name.lower())

        total = len(summaries)
        return DoctorSearchResponse(items=summaries[offset : offset + limit], total=total)

    def list_discovery_facilities(self) -> list[DoctorFacilityOption]:
        return [
            DoctorFacilityOption(
                id=facility.id,
                name=facility.name,
                facility_type=facility.facility_type,
                area=_facility_area(facility),
            )
            for facility in self.repository.list_active_facilities()
        ]

    def get_doctor_profile(self, doctor_user_id: uuid.UUID) -> DoctorProfile:
        registration = self.repository.get_verified_doctor_registration(doctor_user_id)
        if registration is None:
            raise DoctorNotFoundError()
        detail = self.repository.get_doctor_registration_detail(registration.id)
        practice_schedules = self.repository.list_active_schedules_for_doctor(
            doctor_user_id
        )
        practice_days = [_to_practice_day(schedule) for schedule in practice_schedules]
        next_practice = _next_practice(practice_schedules)
        return _to_profile(registration, detail, practice_days, next_practice)

    def get_doctor_practice_days(
        self, doctor_user_id: uuid.UUID
    ) -> list[PracticeDay]:
        registration = self.repository.get_verified_doctor_registration(doctor_user_id)
        if registration is None:
            raise DoctorNotFoundError()
        schedules = self.repository.list_active_schedules_for_doctor(doctor_user_id)
        return [_to_practice_day(schedule) for schedule in schedules]

    def list_eligible_facilities(
        self, doctor_user_id: uuid.UUID
    ) -> list[DoctorFacilityChoice]:
        """List active facilities a verified doctor may attach to a schedule.

        Returns all currently active facilities so the doctor can pick a
        destination. ``is_verified_assignment`` flags facilities where the
        doctor already holds an approved DOCTOR registration; those are
        surfaced first in the UI as a hint.
        """
        registration = self.repository.get_verified_doctor_registration(doctor_user_id)
        if registration is None:
            raise DoctorNotFoundError()
        facilities = self.repository.list_active_facilities()
        verified_ids = self.repository.list_verified_facility_ids(doctor_user_id)
        return [
            DoctorFacilityChoice(
                id=facility.id,
                name=facility.name,
                facility_type=facility.facility_type,
                is_active=facility.is_active,
                is_verified_assignment=facility.id in verified_ids,
            )
            for facility in facilities
        ]

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


def _to_summary(
    registration,
    detail,
    *,
    next_practice: NextPracticeWindow | None = None,
    distance_km: float | None = None,
) -> DoctorSummary:
    profile = registration.professional
    user = _profile_user(profile)
    facility = registration.facility
    specialization_code = DoctorSpecialization(
        detail.specialization if detail else DoctorSpecialization.GENERAL_MEDICINE.value
    )
    return DoctorSummary(
        id=profile.user_id,
        name=f"{user.first_name} {user.last_name}".strip(),
        first_name=user.first_name,
        last_name=user.last_name,
        facility_id=facility.id,
        facility_name=facility.name,
        facility_type=facility.facility_type,
        designation=registration.designation,
        role_code=registration.role.code,
        verified=registration.verification_status == "VERIFIED",
        specialization=DOCTOR_SPECIALIZATION_LABELS[specialization_code],
        specialization_code=specialization_code,
        qualification=detail.qualification if detail else None,
        facility_area=_facility_area(facility),
        next_practice=next_practice,
        distance_km=distance_km,
    )


def _to_profile(
    registration,
    detail,
    practice_days: list[PracticeDay],
    next_practice: NextPracticeWindow | None,
) -> DoctorProfile:
    summary = _to_summary(registration, detail, next_practice=next_practice)
    profile = registration.professional
    user = _profile_user(profile)
    return DoctorProfile(
        **summary.model_dump(),
        email=user.email,
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


def _distance_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius_km = 6371.0088
    lat_delta = radians(lat_b - lat_a)
    lon_delta = radians(lon_b - lon_a)
    start = radians(lat_a)
    end = radians(lat_b)
    value = sin(lat_delta / 2) ** 2 + cos(start) * cos(end) * sin(lon_delta / 2) ** 2
    return 2 * radius_km * asin(sqrt(value))


def _next_practice(schedules: list[DoctorPracticeSchedule]) -> NextPracticeWindow | None:
    if not schedules:
        return None
    now = datetime.now(ZoneInfo("Asia/Dhaka"))
    weekday_index = {
        "MONDAY": 0,
        "TUESDAY": 1,
        "WEDNESDAY": 2,
        "THURSDAY": 3,
        "FRIDAY": 4,
        "SATURDAY": 5,
        "SUNDAY": 6,
    }

    def sort_key(schedule: DoctorPracticeSchedule):
        days = (weekday_index[schedule.weekday] - now.weekday()) % 7
        if days == 0 and schedule.end_time <= now.time().replace(tzinfo=None):
            days = 7
        return days, schedule.start_time

    schedule = min(schedules, key=sort_key)
    days_away = sort_key(schedule)[0]
    return NextPracticeWindow(
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        facility_name=schedule.facility.name if schedule.facility else "",
        days_away=days_away,
    )


def _practice_sort_key(summary: DoctorSummary):
    if summary.next_practice is None:
        return 8, "23:59:59", summary.name.lower()
    return (
        summary.next_practice.days_away,
        summary.next_practice.start_time.isoformat(),
        summary.name.lower(),
    )


def _facility_area(facility) -> str | None:
    if not facility.district_code or not facility.upazila_code:
        return None
    try:
        district, upazila = resolve_area(facility.district_code, facility.upazila_code)
    except BangladeshAreaNotFoundError:
        return None
    return f"{upazila.name}, {district.name}"
