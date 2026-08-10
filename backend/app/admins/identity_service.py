from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admins.identity_repository import CitizenIdentitySupportRepository
from app.admins.identity_schemas import (
    CitizenIdentityCorrectionResponse,
    CitizenIdentityDetail,
    CitizenIdentitySummary,
    CitizenIdentityCorrectionRequest,
)
from app.admins.models import AdminActionLog
from app.auth.models import User
from app.auth.service import utc_now
from app.citizens.constants import CitizenRegistrationMethod
from app.citizens.models import CitizenIdentifier, UserNationalIdentifier
from app.core.exceptions import HealthLinkError


class CitizenNotFoundError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Citizen not found.", status_code=404)


class CitizenIdentityMissingError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__("Citizen has no identity record.", status_code=404)


class CitizenIdentitySearchFilterMissingError(HealthLinkError):
    def __init__(self) -> None:
        super().__init__(
            "Provide at least one of NID, Birth Certificate Number, email, or user ID.",
            status_code=400,
        )


class CitizenIdentityConflictError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


class CitizenIdentityStateError(HealthLinkError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=409)


@dataclass(frozen=True)
class _SummaryInputs:
    user: User
    identity: CitizenIdentifier
    national_identifier: UserNationalIdentifier | None


class CitizenIdentitySupportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = CitizenIdentitySupportRepository(db)

    def search(
        self,
        *,
        nid_number: str | None,
        birth_certificate_number: str | None,
        email: str | None,
        user_id: uuid.UUID | None,
        limit: int,
    ) -> list[CitizenIdentitySummary]:
        if not any(
            value is not None
            for value in (nid_number, birth_certificate_number, email, user_id)
        ):
            raise CitizenIdentitySearchFilterMissingError()

        users = self.repository.search(
            nid_number=nid_number,
            birth_certificate_number=birth_certificate_number,
            email=email,
            user_id=user_id,
            limit=limit,
        )
        summaries: list[CitizenIdentitySummary] = []
        for user in users:
            inputs = self._load_inputs(user.id)
            if inputs is None:
                continue
            summaries.append(self._summary(inputs))
        return summaries

    def detail(self, user_id: uuid.UUID) -> CitizenIdentityDetail:
        user = self.repository.get_user_with_identity(user_id)
        if user is None:
            raise CitizenNotFoundError()
        inputs = self._load_inputs(user.id)
        if inputs is None:
            raise CitizenIdentityMissingError()
        summary = self._summary(inputs)
        profile = self.repository.get_profile_by_user_id(user.id)
        national_identifier = inputs.national_identifier
        session_count = self.repository.count_active_auth_sessions(user.id)
        return CitizenIdentityDetail(
            **summary.model_dump(),
            national_identifier_id=national_identifier.id if national_identifier else None,
            national_identifier_created_at=(
                national_identifier.created_at if national_identifier else None
            ),
            date_of_birth=profile.date_of_birth if profile else None,
            gender=profile.gender if profile else None,
            blood_group=profile.blood_group if profile else None,
            address=profile.address if profile else None,
            auth_session_count=session_count,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def correct(
        self,
        user_id: uuid.UUID,
        request: CitizenIdentityCorrectionRequest,
        *,
        admin_user_id: uuid.UUID,
    ) -> CitizenIdentityCorrectionResponse:
        user = self.repository.get_user_with_identity(user_id)
        if user is None:
            raise CitizenNotFoundError()
        identity = self.repository.get_identity_by_user_id(user_id, for_update=True)
        if identity is None:
            self.db.rollback()
            raise CitizenIdentityMissingError()

        correction_type = request.correction_type
        new_value = request.new_value
        if correction_type == "NID":
            previous_value, audit_payload, target_resource_id = self._correct_nid(
                user_id=user_id,
                identity=identity,
                new_value=new_value,
            )
        else:
            previous_value, audit_payload, target_resource_id = self._correct_bcn(
                identity=identity,
                new_value=new_value,
            )

        audit_log = AdminActionLog(
            admin_user_id=admin_user_id,
            action_type=f"CITIZEN_IDENTITY_CORRECT_{correction_type}",
            target_user_id=user_id,
            target_resource_type=(
                "USER_NATIONAL_IDENTIFIER"
                if correction_type == "NID"
                else "CITIZEN_BIRTH_CERTIFICATE"
            ),
            target_resource_id=target_resource_id,
            reason=request.reason,
        )
        self.db.add(audit_log)

        try:
            self.db.commit()
        except IntegrityError as error:
            self.db.rollback()
            raise CitizenIdentityConflictError(
                "The corrected identity conflicts with another record."
            ) from error
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(audit_log)
        return CitizenIdentityCorrectionResponse(
            user_id=user_id,
            correction_type=correction_type,
            previous_value=previous_value,
            new_value=new_value,
            corrected_at=utc_now(),
            audit_log_id=audit_log.id,
        )

    def _correct_nid(
        self,
        *,
        user_id: uuid.UUID,
        identity: CitizenIdentifier,
        new_value: str,
    ) -> tuple[str | None, str, uuid.UUID]:
        existing = self.repository.get_national_identifier_by_user_id(
            user_id, for_update=True
        )
        if existing is not None:
            conflict = self.repository.get_national_identifier_by_number(new_value)
            if conflict is not None and conflict.id != existing.id:
                self.db.rollback()
                raise CitizenIdentityConflictError(
                    "Another citizen already uses this National ID."
                )
            previous_value = existing.nid_number
            existing.nid_number = new_value
            target_resource_id = existing.id
        else:
            conflict = self.repository.get_national_identifier_by_number(new_value)
            if conflict is not None:
                self.db.rollback()
                raise CitizenIdentityConflictError(
                    "Another citizen already uses this National ID."
                )
            row = UserNationalIdentifier(user_id=user_id, nid_number=new_value)
            self.db.add(row)
            self.db.flush()
            previous_value = None
            target_resource_id = row.id
            identity.national_identifier_id = row.id

        identity.nid_added_at = utc_now()
        return previous_value, new_value, target_resource_id

    def _correct_bcn(
        self,
        *,
        identity: CitizenIdentifier,
        new_value: str,
    ) -> tuple[str | None, str, uuid.UUID]:
        if identity.birth_certificate_number is None:
            self.db.rollback()
            raise CitizenIdentityStateError(
                "Cannot correct a Birth Certificate Number that is not present."
            )
        conflict = self.repository.get_identity_by_birth_certificate(new_value)
        if conflict is not None and conflict.id != identity.id:
            self.db.rollback()
            raise CitizenIdentityConflictError(
                "Another citizen already uses this Birth Certificate Number."
            )
        previous_value = identity.birth_certificate_number
        identity.birth_certificate_number = new_value
        return previous_value, new_value, identity.id

    def _load_inputs(self, user_id: uuid.UUID) -> _SummaryInputs | None:
        identity = self.repository.get_identity_by_user_id(user_id)
        if identity is None:
            return None
        user = self.repository.get_user_with_identity(user_id)
        if user is None:
            return None
        national_identifier = None
        if identity.national_identifier_id is not None:
            national_identifier = self.repository.get_national_identifier_by_id(
                identity.national_identifier_id
            )
        return _SummaryInputs(
            user=user,
            identity=identity,
            national_identifier=national_identifier,
        )

    @staticmethod
    def _summary(inputs: _SummaryInputs) -> CitizenIdentitySummary:
        identity = inputs.identity
        national_identifier = inputs.national_identifier
        registered_with = CitizenRegistrationMethod(identity.registered_with)
        return CitizenIdentitySummary(
            user_id=inputs.user.id,
            email=inputs.user.email,
            first_name=inputs.user.first_name,
            last_name=inputs.user.last_name,
            is_active=inputs.user.is_active,
            registered_with=registered_with,
            nid_number=national_identifier.nid_number if national_identifier else None,
            birth_certificate_number=identity.birth_certificate_number,
            nid_added_at=identity.nid_added_at,
            identity_created_at=identity.created_at,
            identity_updated_at=identity.updated_at,
        )