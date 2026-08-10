from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.constants import Portal
from app.auth.service import AuthenticationError, AuthService, IssuedTokens
from app.citizens.models import UserNationalIdentifier
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.core.security import hash_password, verify_password
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)
from app.professionals.repository import ProfessionalRepository
from app.professionals.schemas import (
    ProfessionalApplicationFields,
    ProfessionalOnboardingRequest,
    ProfessionalRegistrationRequest,
    ProfessionalLoginRequest,
)


_DUMMY_PROFESSIONAL_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "x6UEndDIGINbChliFokAwg$WMEeIYWIpGqFiUdzYGg6peAi29r+B7mSRpjNdS6jsqU"
)


class ProfessionalConflictError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class ProfessionalApplicationError(HealthLinkError):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        super().__init__(detail, status_code=status_code)


@dataclass(frozen=True)
class SubmittedProfessionalApplication:
    user: User
    profile: HealthcareProfessionalProfile
    role: ProfessionalRole
    registration: ProfessionalRoleRegistration


@dataclass(frozen=True)
class ProfessionalLoginResult:
    tokens: IssuedTokens
    role: ProfessionalRole
    registration: ProfessionalRoleRegistration


class ProfessionalService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = ProfessionalRepository(db)

    def _active_role(self, role_code: ProfessionalRoleCode) -> ProfessionalRole:
        role = self.repository.get_role_by_code(role_code.value)
        if role is None or not role.is_active:
            raise ProfessionalApplicationError("Selected professional role is unavailable.")
        return role

    def _create_application(
        self,
        *,
        user: User,
        profile: HealthcareProfessionalProfile,
        role: ProfessionalRole,
        request: ProfessionalApplicationFields,
    ) -> SubmittedProfessionalApplication:
        if self.repository.get_role_registration(profile.id, role.id) is not None:
            raise ProfessionalConflictError(
                "An application for this professional role already exists."
            )
        if (
            request.bmdc_registration_number is not None
            and self.repository.get_doctor_detail_by_bmdc(
                request.bmdc_registration_number
            )
            is not None
        ):
            raise ProfessionalConflictError(
                "BM&DC Registration Number is already registered."
            )

        registration = ProfessionalRoleRegistration(
            professional_id=profile.id,
            role_id=role.id,
            facility_name_submitted=request.facility_name,
            designation=request.designation,
            additional_info=request.additional_info,
            verification_status=VerificationStatus.PENDING.value,
        )
        self.repository.add(registration)
        self.db.flush()
        if role.code == ProfessionalRoleCode.DOCTOR.value:
            assert request.bmdc_registration_number is not None
            self.repository.add(
                DoctorRegistrationDetail(
                    professional_role_registration_id=registration.id,
                    bmdc_registration_number=request.bmdc_registration_number,
                )
            )
        return SubmittedProfessionalApplication(
            user=user,
            profile=profile,
            role=role,
            registration=registration,
        )

    def register_new(
        self, request: ProfessionalRegistrationRequest
    ) -> SubmittedProfessionalApplication:
        email = str(request.email).strip().lower()
        nid_number = request.nid_number.strip()
        if self.repository.get_nid_by_number(nid_number) is not None:
            raise ProfessionalConflictError(
                "This NID belongs to an existing HealthLink account. Sign in and use professional onboarding."
            )
        if self.repository.get_user_by_email(email) is not None:
            raise ProfessionalConflictError("Email is already registered.")
        role = self._active_role(request.role_code)
        user = User(
            email=email,
            password_hash=hash_password(request.password.get_secret_value()),
            first_name=request.first_name,
            last_name=request.last_name,
        )
        try:
            self.repository.add(user)
            self.db.flush()
            self.repository.add(
                UserNationalIdentifier(user_id=user.id, nid_number=nid_number)
            )
            profile = HealthcareProfessionalProfile(user_id=user.id)
            self.repository.add(profile)
            self.db.flush()
            result = self._create_application(
                user=user,
                profile=profile,
                role=role,
                request=request,
            )
            self.db.commit()
            self.db.refresh(result.user)
            self.db.refresh(result.profile)
            self.db.refresh(result.registration)
            return result
        except IntegrityError as error:
            self.db.rollback()
            raise ProfessionalConflictError(
                "Email, NID, professional role, or BM&DC number is already registered."
            ) from error
        except Exception:
            self.db.rollback()
            raise

    def onboard_existing(
        self,
        user_id: uuid.UUID,
        request: ProfessionalOnboardingRequest,
    ) -> SubmittedProfessionalApplication:
        user = self.repository.get_user_by_id_for_update(user_id)
        if user is None or not user.is_active:
            self.db.rollback()
            raise ProfessionalApplicationError("Active account required.", status_code=403)
        if self.repository.get_nid_by_user_id(user_id) is None:
            self.db.rollback()
            raise ProfessionalConflictError(
                "Add a National ID to this account before professional onboarding."
            )
        role = self._active_role(request.role_code)
        profile = self.repository.get_profile_by_user_id(user_id)
        try:
            if profile is None:
                profile = HealthcareProfessionalProfile(user_id=user_id)
                self.repository.add(profile)
                self.db.flush()
            result = self._create_application(
                user=user,
                profile=profile,
                role=role,
                request=request,
            )
            self.db.commit()
            self.db.refresh(result.profile)
            self.db.refresh(result.registration)
            return result
        except IntegrityError as error:
            self.db.rollback()
            raise ProfessionalConflictError(
                "Professional role or BM&DC Registration Number is already registered."
            ) from error
        except Exception:
            self.db.rollback()
            raise

    def login(self, request: ProfessionalLoginRequest) -> ProfessionalLoginResult:
        national_identifier = self.repository.get_nid_by_number(request.nid_number)
        user = (
            self.repository.get_user_by_id_for_update(national_identifier.user_id)
            if national_identifier is not None
            else None
        )
        password_matches = verify_password(
            request.password.get_secret_value(),
            user.password_hash if user is not None else _DUMMY_PROFESSIONAL_PASSWORD_HASH,
        )
        profile = self.repository.get_profile_by_user_id(user.id) if user else None
        role = self.repository.get_role_by_code(request.role_code.value)
        registration = (
            self.repository.get_role_registration(profile.id, role.id)
            if profile is not None and role is not None
            else None
        )
        if (
            user is None
            or not user.is_active
            or not password_matches
            or role is None
            or not role.is_active
            or registration is None
        ):
            self.db.rollback()
            raise AuthenticationError("Invalid NID, password, or professional role.")
        tokens = AuthService(self.db, self.settings).create_session(
            user.id,
            Portal.PROFESSIONAL,
            active_professional_role_registration_id=registration.id,
        )
        return ProfessionalLoginResult(
            tokens=tokens,
            role=role,
            registration=registration,
        )
