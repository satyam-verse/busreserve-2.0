"""Database models for isolated AI conversation history and daily quota tracking."""

import json
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AIConversationMessage(db.Model):
    """Per-user isolated AI conversation turns across passenger and admin portals."""

    __tablename__ = "ai_conversation_messages"

    PORTAL_PASSENGER = "PASSENGER"
    PORTAL_ADMIN = "ADMIN"

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    portal = db.Column(
        db.String(20),
        nullable=False,
        default=PORTAL_PASSENGER,
        server_default=PORTAL_PASSENGER,
        index=True,
    )
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(40), nullable=True)
    mode = db.Column(db.String(40), nullable=True)
    intent = db.Column(db.String(60), nullable=True)
    fallback_used = db.Column(db.Boolean, nullable=False, default=False)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    user = db.relationship("User", lazy="select")

    __table_args__ = (
        CheckConstraint(
            "portal IN ('PASSENGER', 'ADMIN')",
            name="ck_ai_messages_valid_portal",
        ),
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_ai_messages_valid_role",
        ),
        Index(
            "ix_ai_messages_user_portal_created",
            "user_id",
            "portal",
            "created_at",
        ),
    )

    def get_metadata(self) -> dict:
        if not self.metadata_json:
            return {}
        try:
            parsed = json.loads(self.metadata_json)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}

    def set_metadata(self, value: dict | None) -> None:
        if not value:
            self.metadata_json = None
            return
        self.metadata_json = json.dumps(value, default=str)[:4000]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "portal": self.portal,
            "role": self.role,
            "content": self.content,
            "provider": self.provider,
            "mode": self.mode,
            "intent": self.intent,
            "fallback_used": self.fallback_used,
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AIUsageDaily(db.Model):
    """Atomic daily usage counter in PostgreSQL for free-tier quota protection."""

    __tablename__ = "ai_usage_daily"

    GLOBAL_SCOPE = "global"

    id = db.Column(db.Integer, primary_key=True)
    usage_date = db.Column(db.Date, nullable=False, index=True)
    scope_key = db.Column(db.String(64), nullable=False)
    gemini_requests = db.Column(db.Integer, nullable=False, default=0)
    fallback_requests = db.Column(db.Integer, nullable=False, default=0)
    failed_requests = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    __table_args__ = (
        UniqueConstraint("usage_date", "scope_key", name="uq_ai_usage_daily_scope"),
        CheckConstraint("gemini_requests >= 0", name="ck_ai_usage_gemini_non_negative"),
        CheckConstraint("fallback_requests >= 0", name="ck_ai_usage_fallback_non_negative"),
        CheckConstraint("failed_requests >= 0", name="ck_ai_usage_failed_non_negative"),
    )

    @classmethod
    def user_scope(cls, user_id: int) -> str:
        return f"user:{user_id}"

    def to_dict(self) -> dict:
        return {
            "usage_date": self.usage_date.isoformat(),
            "scope_key": self.scope_key,
            "gemini_requests": self.gemini_requests,
            "fallback_requests": self.fallback_requests,
            "failed_requests": self.failed_requests,
        }
