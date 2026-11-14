"""User and AuthSession database models for RBAC authentication and session revocation."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(db.Model):
    """Registered passenger or administrator account."""

    __tablename__ = "users"

    ROLE_USER = "USER"
    ROLE_ADMIN = "ADMIN"
    ROLE_DRIVER = "DRIVER"
    ROLE_OPERATOR = "OPERATOR"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_USER, index=True)
    operator_id = db.Column(
        db.Integer,
        db.ForeignKey("operators.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    email_verification_token_hash = db.Column(db.String(64), nullable=True, index=True)
    email_verification_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    password_reset_token_hash = db.Column(db.String(64), nullable=True, index=True)
    password_reset_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    sessions = db.relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    bookings = db.relationship("Booking", back_populates="user", lazy="select")

    __table_args__ = (
        CheckConstraint(
            "role IN ('USER', 'ADMIN', 'DRIVER', 'OPERATOR')",
            name="ck_users_valid_role",
        ),
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password, method="scrypt")

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "operator_id": self.operator_id,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuthSession(db.Model):
    """Issued JWT session tracked in PostgreSQL for immediate server-side revocation."""

    __tablename__ = "auth_sessions"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(64), nullable=False, unique=True, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(20), nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="sessions", lazy="joined")

    def is_valid(self, now: datetime | None = None) -> bool:
        check_now = now or _utcnow()
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.revoked_at is None and expires > check_now

    def to_dict(self, current_jti: str | None = None) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "is_active": self.is_valid(),
            "is_current": bool(current_jti and self.jti == current_jti),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
