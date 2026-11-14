"""Add payment_transactions and notifications tables

Revision ID: e5192c73d81b
Revises: 9b2e7c14f8a1
Create Date: 2026-11-13 00:56:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e5192c73d81b"
down_revision = "9b2e7c14f8a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_ref", sa.String(length=32), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("gateway", sa.String(length=30), nullable=False, server_default="MOCK_SANDBOX"),
        sa.Column("gateway_order_id", sa.String(length=100), nullable=True),
        sa.Column("gateway_payment_id", sa.String(length=100), nullable=True),
        sa.Column("gateway_signature", sa.String(length=255), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="INITIATED"),
        sa.Column("payment_method", sa.String(length=30), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name="fk_payment_transactions_booking_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_payment_transactions_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_transactions_idempotency_key"),
        sa.UniqueConstraint("transaction_ref", name="uq_payment_transactions_transaction_ref"),
    )
    op.create_index(
        "ix_payment_transactions_transaction_ref",
        "payment_transactions",
        ["transaction_ref"],
    )
    op.create_index(
        "ix_payment_transactions_booking_id",
        "payment_transactions",
        ["booking_id"],
    )
    op.create_index(
        "ix_payment_transactions_user_id",
        "payment_transactions",
        ["user_id"],
    )
    op.create_index(
        "ix_payment_transactions_status",
        "payment_transactions",
        ["status"],
    )
    op.create_index(
        "ix_payment_transactions_gateway_order_id",
        "payment_transactions",
        ["gateway_order_id"],
    )
    op.create_index(
        "ix_payment_transactions_gateway_payment_id",
        "payment_transactions",
        ["gateway_payment_id"],
    )
    op.create_index(
        "ix_payment_transactions_created_at",
        "payment_transactions",
        ["created_at"],
    )
    op.create_index(
        "ix_payment_tx_booking_status",
        "payment_transactions",
        ["booking_id", "status"],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="IN_APP"),
        sa.Column("recipient", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SENT"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name="fk_notifications_booking_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
    )
    op.create_index(
        "ix_notifications_booking_id",
        "notifications",
        ["booking_id"],
    )
    op.create_index(
        "ix_notifications_event_type",
        "notifications",
        ["event_type"],
    )
    op.create_index(
        "ix_notifications_is_read",
        "notifications",
        ["is_read"],
    )
    op.create_index(
        "ix_notifications_created_at",
        "notifications",
        ["created_at"],
    )


def downgrade():
    op.drop_table("notifications")
    op.drop_table("payment_transactions")
