"""Add verified payment transactions and a unified 5% commission ledger.

Revision ID: 0008_commission_ledger
Revises: 0007_unique_user_roles
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_commission_ledger"
down_revision = "0007_unique_user_roles"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(60), nullable=False),
        sa.Column("external_payment_id", sa.String(160), nullable=False),
        sa.Column("order_type", sa.String(60), nullable=False),
        sa.Column("order_id", sa.String(100), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("buyer_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("gross_amount", sa.Integer(), nullable=False),
        sa.Column("commission_rate_bps", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("commission_amount", sa.Integer(), nullable=False),
        sa.Column("provider_net_amount", sa.Integer(), nullable=False),
        sa.Column("refunded_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refunded_commission", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="paid"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "external_payment_id", name="uq_payment_provider_external_id"),
        sa.CheckConstraint("gross_amount > 0", name="ck_payment_gross_positive"),
        sa.CheckConstraint("refunded_amount >= 0 AND refunded_amount <= gross_amount", name="ck_payment_refund_bounds"),
    )
    for column in ("order_type", "order_id", "category", "buyer_user_id", "provider_user_id", "status"):
        op.create_index(f"ix_payment_transactions_{column}", "payment_transactions", [column])
    op.create_table(
        "commission_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payment_transactions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_key", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("gross_delta", sa.Integer(), nullable=False),
        sa.Column("commission_delta", sa.Integer(), nullable=False),
        sa.Column("provider_net_delta", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("event_key", name="uq_commission_ledger_event_key"),
        sa.CheckConstraint("gross_delta >= 0 AND commission_delta >= 0", name="ck_commission_ledger_nonnegative"),
    )
    op.create_index("ix_commission_ledger_payment_id", "commission_ledger", ["payment_id"])


def downgrade():
    op.drop_index("ix_commission_ledger_payment_id", table_name="commission_ledger")
    op.drop_table("commission_ledger")
    for column in ("order_type", "order_id", "category", "buyer_user_id", "provider_user_id", "status"):
        op.drop_index(f"ix_payment_transactions_{column}", table_name="payment_transactions")
    op.drop_table("payment_transactions")
