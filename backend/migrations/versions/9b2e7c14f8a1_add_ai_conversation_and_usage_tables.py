"""Add AI conversation history and daily quota tracking tables

Revision ID: 9b2e7c14f8a1
Revises: 4104dd09753c
Create Date: 2026-11-12 01:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b2e7c14f8a1"
down_revision = "4104dd09753c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_conversation_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("portal", sa.String(length=20), server_default="PASSENGER", nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("mode", sa.String(length=40), nullable=True),
        sa.Column("intent", sa.String(length=60), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("portal IN ('PASSENGER', 'ADMIN')", name="ck_ai_messages_valid_portal"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_ai_messages_valid_role"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_conversation_messages_user_id",
        "ai_conversation_messages",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_conversation_messages_portal",
        "ai_conversation_messages",
        ["portal"],
        unique=False,
    )
    op.create_index(
        "ix_ai_conversation_messages_created_at",
        "ai_conversation_messages",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_messages_user_portal_created",
        "ai_conversation_messages",
        ["user_id", "portal", "created_at"],
        unique=False,
    )

    op.create_table(
        "ai_usage_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("gemini_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("gemini_requests >= 0", name="ck_ai_usage_gemini_non_negative"),
        sa.CheckConstraint("fallback_requests >= 0", name="ck_ai_usage_fallback_non_negative"),
        sa.CheckConstraint("failed_requests >= 0", name="ck_ai_usage_failed_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usage_date", "scope_key", name="uq_ai_usage_daily_scope"),
    )
    op.create_index(
        "ix_ai_usage_daily_usage_date",
        "ai_usage_daily",
        ["usage_date"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_ai_usage_daily_usage_date", table_name="ai_usage_daily")
    op.drop_table("ai_usage_daily")

    op.drop_index("ix_ai_messages_user_portal_created", table_name="ai_conversation_messages")
    op.drop_index("ix_ai_conversation_messages_created_at", table_name="ai_conversation_messages")
    op.drop_index("ix_ai_conversation_messages_portal", table_name="ai_conversation_messages")
    op.drop_index("ix_ai_conversation_messages_user_id", table_name="ai_conversation_messages")
    op.drop_table("ai_conversation_messages")
