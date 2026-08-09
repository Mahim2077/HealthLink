from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import User
from app.auth.service import AuthenticationError, AuthService, IssuedTokens
from app.citizens.constants import CitizenRegistrationMethod
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)
from app.citizens.repository import CitizenRepository
from app.citizens.schemas import CitizenLoginRequest, CitizenRegistrationRequest
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.core.security import hash_password, verify_password


# This valid, precomputed Argon2id hash is deliberately unrelated to any user.
# It keeps unknown-account login attempts on the same password-verification path
# without performing expensive hashing at import or request time.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "x6UEndDIGINbChliFokAwg$WMEeIYWIpGqFiUdzYGg6peAi29r+B7mSRpjNdS6jsqU"
)


class CitizenRegistrationError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=400)


class CitizenConflictError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class CitizenCapabilityError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Citizen profile required.", status_code=403)


@dataclass(frozen=True)
class RegisteredCitizen:
    user: User
    profile: CitizenProfile
    identity: CitizenIdentifier


@dataclass(frozen=True)
class CitizenIdentityDetails:
    identity: CitizenIdentifier
    national_identifier: UserNationalIdentifier | None


class CitizenService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = CitizenRepository(db)

    @staticmethod
    def _normalized_identity(
        nid_number: str | None,
        birth_certificate_number: str | None,
    ) -> tuple[str | None, str | None, CitizenRegistrationMethod]:
        nid = nid_number.strip() if nid_number else None
        bcn = birth_certificate_number.strip() if birth_certificate_number else None
        nid = nid or None
        bcn = bcn or None
        if (nid is None) == (bcn is None):
            raise CitizenRegistrationError(
                "Provide exactly one of NID or Birth Certificate Number."
            )
        method = (
            CitizenRegistrationMethod.NID
            if nid is not None
            else CitizenRegistrationMethod.BCN
        )
        return nid, bcn, method

    def register(self, request: CitizenRegistrationRequest) -> RegisteredCitizen:
        nid_number, birth_certificate_number, method = self._normalized_identity(
            request.nid_number,
            request.birth_certificate_number,
        )
        email = str(request.email).strip().lower()
        if self.repository.get_user_by_email(email) is not None:
            raise CitizenConflictError("Email is already registered.")
        if (
            nid_number is not None
            and self.repository.get_national_identifier_by_number(nid_number)
            is not None
        ):
            raise CitizenConflictError("NID is already registered.")
        if (
            birth_certificate_number is not None
            and self.repository.get_identity_by_birth_certificate(
                birth_certificate_number
            )
            is not None
        ):
            raise CitizenConflictError(
                "Birth Certificate Number is already registered."
            )

        user = User(
            email=email,
            password_hash=hash_password(request.password.get_secret_value()),
            first_name=request.first_name,
            last_name=request.last_name,
        )
        profile = CitizenProfile(
            user_id=user.id,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            blood_group=request.blood_group,
            address=request.address,
        )
        try:
            self.repository.add(user)
            self.db.flush()
            profile.user_id = user.id
            self.repository.add(profile)

            national_identifier: UserNationalIdentifier | None = None
            if nid_number is not None:
                national_identifier = UserNationalIdentifier(
                    user_id=user.id,
                    nid_number=nid_number,
                )
                self.repository.add(national_identifier)
                self.db.flush()

            identity = CitizenIdentifier(
                user_id=user.id,
                national_identifier_id=(
                    national_identifier.id if national_identifier is not None else None
                ),
                birth_certificate_number=birth_certificate_number,
                registered_with=method.value,
            )
            self.repository.add(identity)
            self.db.commit()
            self.db.refresh(user)
            self.db.refresh(profile)
            self.db.refresh(identity)
            return RegisteredCitizen(user=user, profile=profile, identity=identity)
        except IntegrityError as error:
            self.db.rollback()
            raise CitizenConflictError(
                "Email or citizen identity is already registered."
            ) from error
        except Exception:
            self.db.rollback()
            raise

    def login(self, request: CitizenLoginRequest) -> IssuedTokens:
        email = str(request.email).strip().lower()
        user = self.repository.get_user_by_email(email)
        password_matches = verify_password(
            request.password.get_secret_value(),
            user.password_hash if user is not None else _DUMMY_PASSWORD_HASH,
        )
        profile = (
            self.repository.get_profile_by_user_id(user.id)
            if user is not None
            else None
        )
        if (
            user is None
            or not user.is_active
            or not password_matches
            or profile is None
        ):
            raise AuthenticationError("Invalid email or password.")
        return AuthService(self.db, self.settings).create_session(
            user.id,
            Portal.CITIZEN,
        )

    def get_profile(self, user_id: uuid.UUID) -> CitizenProfile:
        profile = self.repository.get_profile_by_user_id(user_id)
        if profile is None:
            raise CitizenCapabilityError()
        return profile

    def get_identity(self, user_id: uuid.UUID) -> CitizenIdentityDetails:
        identity = self.repository.get_identity_by_user_id(user_id)
        if identity is None:
            raise CitizenCapabilityError()
        national_identifier = None
        if identity.national_identifier_id is not None:
            national_identifier = self.repository.get_national_identifier_by_id(
                identity.national_identifier_id
            )
        return CitizenIdentityDetails(
            identity=identity,
            national_identifier=national_identifier,
        )
