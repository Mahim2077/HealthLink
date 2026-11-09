from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import case, delete, or_, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.admins.repository import AdminRepository
from app.auth.constants import Portal
from app.auth.models import EmailCodeChallenge, EmailCodeRateLimit, User
from app.auth.repository import AuthRepository
from app.auth.service import as_utc, utc_now
from app.citizens.repository import CitizenRepository
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.core.security import hash_password, verify_password
from app.professionals.constants import ProfessionalRoleCode
from app.professionals.repository import ProfessionalRepository


CODE_LIFETIME = timedelta(minutes=10)
RESEND_SECONDS = 60
MAX_ATTEMPTS = 5
SIGNUP = "signup"
ENROLL = "enroll"
RESET = "reset"


@dataclass(frozen=True)
class EmailCodeDelivery:
    challenge_id: uuid.UUID
    code: str
    recipient: str


def _invalid_code() -> HealthLinkError:
    return HealthLinkError("Invalid or expired code. Check the code or request a new one.", status_code=400)


class EmailCodeService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def require_enabled(self) -> None:
        if not self.settings.auth_email_otp_enabled:
            raise HealthLinkError("Email verification and password recovery are unavailable.", status_code=503)

    def _digest(self, *parts: str) -> str:
        return hmac.new(
            self.settings.auth_email_otp_secret.encode(),
            json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode(),
            hashlib.sha256,
        ).hexdigest()

    def _limit(self, key: str, *, limit: int, now: datetime, window: timedelta) -> bool:
        insert = sqlite_insert if self.db.get_bind().dialect.name == "sqlite" else postgres_insert
        expires = now + window
        expired = EmailCodeRateLimit.expires_at <= now
        statement = insert(EmailCodeRateLimit).values(key=key, count=1, expires_at=expires)
        upsert = statement.on_conflict_do_update(
            index_elements=[EmailCodeRateLimit.key],
            set_={
                "count": case((expired, 1), else_=EmailCodeRateLimit.count + 1),
                "expires_at": case((expired, expires), else_=EmailCodeRateLimit.expires_at),
            },
            where=or_(expired, EmailCodeRateLimit.count < limit),
        ).returning(EmailCodeRateLimit.key)
        return self.db.scalar(upsert) is not None

    def check_request_rate(self, client_address: str) -> None:
        self.require_enabled()
        now = utc_now()
        allowed = self._limit(
            self._digest("client", client_address), limit=20, now=now, window=timedelta(minutes=15),
        )
        self.db.commit()
        if not allowed:
            raise HealthLinkError("Too many requests. Try again in a few minutes.", status_code=429)

    def _can_send(self, recipient: str, now: datetime) -> bool:
        return (
            self._limit(self._digest("cooldown", recipient), limit=1, now=now, window=timedelta(seconds=RESEND_SECONDS))
            and self._limit(self._digest("hour", recipient), limit=5, now=now, window=timedelta(hours=1))
            and self._limit(self._digest("delivery"), limit=250, now=now, window=timedelta(days=1))
        )

    def _account_hash(self, user: User) -> str:
        verified_at = as_utc(user.email_verified_at).isoformat() if user.email_verified_at else ""
        return self._digest("account", str(user.id), user.email, user.password_hash, verified_at)

    def _new_challenge(
        self, purpose: str, scope: str, recipient: str | None, user: User | None = None,
    ) -> tuple[uuid.UUID, EmailCodeDelivery | None]:
        now = utc_now()
        can_send = recipient is not None and self._can_send(recipient, now)
        self.db.execute(
            delete(EmailCodeChallenge)
            .where(EmailCodeChallenge.expires_at < now - CODE_LIFETIME)
            .execution_options(synchronize_session="fetch"),
        )
        self.db.execute(
            delete(EmailCodeRateLimit)
            .where(EmailCodeRateLimit.expires_at < now - timedelta(days=1))
            .execution_options(synchronize_session=False),
        )
        challenge_id = uuid.uuid4()
        if not can_send and purpose != RESET:
            self.db.commit()
            raise HealthLinkError("Please wait before requesting another code.", status_code=429)

        code = f"{secrets.randbelow(1_000_000):06d}"
        if can_send:
            self.db.execute(delete(EmailCodeChallenge).where(EmailCodeChallenge.scope_hash == scope))
        self.db.add(EmailCodeChallenge(
            id=challenge_id,
            purpose=purpose,
            scope_hash=scope if can_send else self._digest("decoy", str(challenge_id)),
            user_id=user.id if can_send and user else None,
            account_hash=self._account_hash(user) if can_send and user else None,
            code_hash=self._digest("code", str(challenge_id), code),
            expires_at=now + CODE_LIFETIME,
        ))
        self.db.commit()
        delivery = EmailCodeDelivery(challenge_id, code, recipient) if can_send and recipient is not None else None
        return challenge_id, delivery

    def start_signup(self, email: str, portal: Portal) -> EmailCodeDelivery:
        _, delivery = self._new_challenge(SIGNUP, self._digest(SIGNUP, portal.value, email), email)
        assert delivery is not None
        return delivery

    def start_enrollment(self, user: User, password: str) -> EmailCodeDelivery:
        if not verify_password(password, user.password_hash):
            raise HealthLinkError("Current password is incorrect.", status_code=400)
        if user.email_verified_at is not None:
            raise HealthLinkError("This email is already verified.", status_code=409)
        _, delivery = self._new_challenge(ENROLL, self._digest(ENROLL, str(user.id)), user.email, user)
        assert delivery is not None
        return delivery

    def start_reset(
        self, portal: Portal, identifier: str, role_code: ProfessionalRoleCode | None,
    ) -> tuple[uuid.UUID, EmailCodeDelivery | None]:
        if portal is Portal.PROFESSIONAL:
            repository = ProfessionalRepository(self.db)
            nid = repository.get_nid_by_number(identifier)
            user = self.db.get(User, nid.user_id) if nid is not None else None
            profile = repository.get_profile_by_user_id(user.id) if user else None
            role = repository.get_role_by_code(role_code.value) if role_code else None
            eligible = bool(
                profile and role and role.is_active and repository.get_role_registration(profile.id, role.id),
            )
        else:
            citizens = CitizenRepository(self.db)
            user = citizens.get_user_by_email(identifier)
            if portal is Portal.ADMIN:
                admin = AdminRepository(self.db).get_admin_by_user_id(user.id) if user else None
                eligible = bool(admin and admin.is_active)
            else:
                eligible = bool(user and citizens.get_profile_by_user_id(user.id))
        if user and user.is_active and user.email_verified_at is not None and eligible:
            return self._new_challenge(RESET, self._digest(RESET, str(user.id)), user.email, user)
        return self._new_challenge(RESET, "", None)

    def _challenge(self, challenge_id: uuid.UUID, purpose: str) -> EmailCodeChallenge | None:
        return self.db.scalar(
            select(EmailCodeChallenge)
            .where(EmailCodeChallenge.id == challenge_id, EmailCodeChallenge.purpose == purpose)
            .with_for_update()
            .execution_options(populate_existing=True),
        )

    def _check_code(
        self, challenge_id: uuid.UUID, purpose: str, code: str,
    ) -> EmailCodeChallenge:
        challenge = self._challenge(challenge_id, purpose)
        if (
            challenge is None or challenge.code_hash is None
            or challenge.attempts >= MAX_ATTEMPTS or as_utc(challenge.expires_at) <= utc_now()
        ):
            raise _invalid_code()
        if not hmac.compare_digest(challenge.code_hash, self._digest("code", str(challenge_id), code)):
            challenge.attempts += 1
            self.db.commit()
            raise _invalid_code()
        return challenge

    def verify_signup(
        self, portal: Portal, email: str, challenge_id: uuid.UUID | None, code: str | None,
    ) -> datetime | None:
        if not self.settings.auth_email_otp_enabled:
            return None
        if challenge_id is None or code is None:
            raise HealthLinkError("Verify your email to finish registration.", status_code=428)
        challenge = self._check_code(challenge_id, SIGNUP, code)
        if not hmac.compare_digest(challenge.scope_hash, self._digest(SIGNUP, portal.value, email)):
            raise _invalid_code()
        # The registration transaction consumes the code only if account creation succeeds.
        self.db.delete(challenge)
        return utc_now()

    def _bound_user(self, challenge: EmailCodeChallenge) -> User | None:
        if challenge.user_id is None:
            return None
        user = CitizenRepository(self.db).get_user_by_id(challenge.user_id, for_update=True)
        if user is None or not user.is_active or not hmac.compare_digest(
            challenge.account_hash or "", self._account_hash(user),
        ):
            return None
        return user

    def verify_enrollment(self, user_id: uuid.UUID, challenge_id: uuid.UUID, code: str) -> None:
        challenge = self._check_code(challenge_id, ENROLL, code)
        user = self._bound_user(challenge) if challenge.user_id == user_id else None
        if user is None:
            raise _invalid_code()
        user.email_verified_at = utc_now()
        self.db.delete(challenge)
        self.db.commit()

    def verify_reset(self, challenge_id: uuid.UUID, code: str) -> str:
        challenge = self._check_code(challenge_id, RESET, code)
        user = self._bound_user(challenge)
        if user is None or user.email_verified_at is None:
            raise _invalid_code()
        token = secrets.token_urlsafe(32)
        challenge.code_hash = None
        challenge.reset_hash = self._digest("reset-token", str(challenge_id), token)
        challenge.expires_at = utc_now() + CODE_LIFETIME
        self.db.commit()
        return token

    def complete_reset(self, challenge_id: uuid.UUID, token: str, password: str) -> str:
        challenge = self._challenge(challenge_id, RESET)
        if (
            challenge is None or challenge.reset_hash is None
            or as_utc(challenge.expires_at) <= utc_now()
            or not hmac.compare_digest(challenge.reset_hash, self._digest("reset-token", str(challenge_id), token))
        ):
            raise HealthLinkError("This reset has expired. Request a new code.", status_code=400)
        user = self._bound_user(challenge)
        if user is None or user.email_verified_at is None:
            raise HealthLinkError("This reset has expired. Request a new code.", status_code=400)
        email = user.email
        user.password_hash = hash_password(password)
        AuthRepository(self.db).revoke_active_sessions(user.id, utc_now())
        self.db.delete(challenge)
        self.db.commit()
        return email
