"""Authentication, email verification, password reset, profile, and session services."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import select, update

from app.extensions import db
from app.models import AuthSession, User
from app.services.mail_service import dispatch_transactional_email
from app.utils.auth import create_user_session, generate_secure_token, hash_token
from app.utils.errors import ConflictError, ForbiddenError, UnauthorizedError, ValidationAPIError

logger = logging.getLogger("busreserve.auth_service")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def register_user(payload: dict[str, Any]) -> tuple[User, dict[str, str] | None]:
    """Create a new USER account with scrypt password hash and email verification token."""
    email = payload["email"].strip().lower()
    existing = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "An account with this email address already exists.",
            details={"email": ["Email is already registered."]},
        )

    raw_token = generate_secure_token()
    expires_at = _utcnow() + timedelta(minutes=current_app.config["EMAIL_TOKEN_EXPIRES_MINUTES"])

    user = User(
        email=email,
        full_name=payload["full_name"].strip(),
        phone=payload.get("phone"),
        role=User.ROLE_USER,
        is_active=True,
        email_verified=False,
        email_verification_token_hash=hash_token(raw_token),
        email_verification_expires_at=expires_at,
    )
    user.set_password(payload["password"])
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)

    preview = dispatch_transactional_email(
        recipient=user.email,
        subject="Verify your BusReserve account",
        body_text="Please verify your email address to activate your BusReserve account.",
        action_path="/verify-email",
        raw_token=raw_token,
    )
    logger.info("user_registered", extra={"user_id": user.id})
    return user, preview


def verify_user_email(raw_token: str) -> User:
    """Verify a user's email address using a single-use cryptographic token."""
    token_hash = hash_token(raw_token.strip())
    user = db.session.execute(
        select(User).where(User.email_verification_token_hash == token_hash)
    ).scalar_one_or_none()

    if user is None:
        raise ValidationAPIError(
            "Verification link is invalid or has already been used.",
            details={"token": ["Invalid email verification token."]},
        )

    expires_at = _as_utc(user.email_verification_expires_at)
    if expires_at is None or expires_at <= _utcnow():
        raise ValidationAPIError(
            "Verification token has expired. Request a new verification email.",
            details={"token": ["Verification token expired."]},
        )

    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.session.commit()
    db.session.refresh(user)
    logger.info("user_email_verified", extra={"user_id": user.id})
    return user


def resend_verification(email: str) -> dict[str, str] | None:
    """Issue a fresh verification token if an unverified active USER exists."""
    clean_email = email.strip().lower()
    user = db.session.execute(select(User).where(User.email == clean_email)).scalar_one_or_none()
    if user is None or not user.is_active or user.email_verified:
        return None

    raw_token = generate_secure_token()
    user.email_verification_token_hash = hash_token(raw_token)
    user.email_verification_expires_at = _utcnow() + timedelta(
        minutes=current_app.config["EMAIL_TOKEN_EXPIRES_MINUTES"]
    )
    db.session.commit()

    return dispatch_transactional_email(
        recipient=user.email,
        subject="Verify your BusReserve account",
        body_text="Here is your new BusReserve email verification link.",
        action_path="/verify-email",
        raw_token=raw_token,
    )


def authenticate_account(
    email: str,
    password: str,
    required_role: str,
) -> tuple[User, AuthSession, str, datetime]:
    """Authenticate credentials strictly within a specific portal role (USER vs ADMIN)."""
    clean_email = email.strip().lower()
    user = db.session.execute(select(User).where(User.email == clean_email)).scalar_one_or_none()

    if user is None or not user.check_password(password):
        logger.warning(
            "auth_login_failed",
            extra={"portal_role": required_role, "reason": "invalid_credentials"},
        )
        raise UnauthorizedError("Invalid email or password.")

    if not user.is_active:
        logger.warning(
            "auth_login_blocked_inactive",
            extra={"user_id": user.id, "portal_role": required_role},
        )
        raise ForbiddenError("This account has been deactivated. Contact support.")

    if user.role != required_role:
        logger.warning(
            "auth_portal_role_mismatch",
            extra={"user_id": user.id, "actual_role": user.role, "portal_role": required_role},
        )
        if required_role == User.ROLE_ADMIN:
            raise ForbiddenError("Administrator privileges are required for this portal.")
        raise ForbiddenError("Administrator accounts must sign in via the Admin Portal.")

    if not user.email_verified:
        raise ForbiddenError(
            "Please verify your email address before signing in.",
            error_code="email_not_verified",
        )

    session_obj, token, expires_at = create_user_session(user)
    db.session.commit()
    db.session.refresh(user)
    logger.info("auth_login_succeeded", extra={"user_id": user.id, "role": user.role})
    return user, session_obj, token, expires_at


def request_password_reset(email: str) -> dict[str, str] | None:
    """Create a single-use password reset token without leaking account existence."""
    clean_email = email.strip().lower()
    user = db.session.execute(select(User).where(User.email == clean_email)).scalar_one_or_none()
    if user is None or not user.is_active or user.role != User.ROLE_USER:
        return None

    raw_token = generate_secure_token()
    user.password_reset_token_hash = hash_token(raw_token)
    user.password_reset_expires_at = _utcnow() + timedelta(
        minutes=current_app.config["RESET_TOKEN_EXPIRES_MINUTES"]
    )
    db.session.commit()

    return dispatch_transactional_email(
        recipient=user.email,
        subject="Reset your BusReserve password",
        body_text="Use the link below to reset your BusReserve password.",
        action_path="/reset-password",
        raw_token=raw_token,
    )


def reset_password_with_token(raw_token: str, new_password: str) -> User:
    """Reset password with a valid token and immediately revoke all active sessions."""
    token_hash = hash_token(raw_token.strip())
    user = db.session.execute(
        select(User).where(User.password_reset_token_hash == token_hash)
    ).scalar_one_or_none()

    if user is None:
        raise ValidationAPIError(
            "Password reset link is invalid or has already been used.",
            details={"token": ["Invalid password reset token."]},
        )

    expires_at = _as_utc(user.password_reset_expires_at)
    if expires_at is None or expires_at <= _utcnow():
        raise ValidationAPIError(
            "Password reset link has expired. Please request a new one.",
            details={"token": ["Password reset token expired."]},
        )

    user.set_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None

    # Revoke all existing sessions whenever a password is reset
    db.session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
    )
    db.session.commit()
    db.session.refresh(user)
    logger.info("password_reset_completed", extra={"user_id": user.id})
    return user


def revoke_session(session_obj: AuthSession) -> None:
    """Revoke a single authentication session."""
    session_obj.revoked_at = _utcnow()
    db.session.commit()


def revoke_all_user_sessions(user_id: int) -> int:
    """Revoke all active sessions belonging to a user."""
    result = db.session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
    )
    db.session.commit()
    return int(result.rowcount or 0)


def update_user_profile(user: User, payload: dict[str, Any]) -> User:
    """Update authenticated user's profile fields."""
    if "full_name" in payload:
        user.full_name = payload["full_name"].strip()
    if "phone" in payload:
        user.phone = payload["phone"]
    db.session.commit()
    db.session.refresh(user)
    return user


def change_user_password(
    user: User,
    current_password: str,
    new_password: str,
    current_session_jti: str,
) -> None:
    """Verify current password, set new hash, and revoke other active sessions."""
    if not user.check_password(current_password):
        raise UnauthorizedError("Current password is incorrect.")
    user.set_password(new_password)
    db.session.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.jti != current_session_jti,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=_utcnow())
    )
    db.session.commit()
    logger.info("user_password_changed", extra={"user_id": user.id})


def list_user_sessions(user_id: int, current_jti: str | None = None) -> list[dict[str, Any]]:
    """Return recent and active sessions for account management."""
    sessions = (
        db.session.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .order_by(AuthSession.created_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    return [s.to_dict(current_jti=current_jti) for s in sessions]
