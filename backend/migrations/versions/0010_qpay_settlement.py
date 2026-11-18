"""Add provider-level commission allocations and QPay invoice records.

Revision ID: 0010_qpay_settlement
Revises: 0009_qpay_invoices
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_qpay_settlement"
down_revision = "0009_qpay_invoices"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("payment_transactions") as batch:
        batch.alter_column("provider_user_id", existing_type=sa.Integer(), nullable=True)
    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payment_transactions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("provider_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("gross_amount", sa.Integer(), nullable=False),
        sa.Column("commission_amount", sa.Integer(), nullable=False),
        sa.Column("provider_net_amount", sa.Integer(), nullable=False),
        sa.Column("refunded_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("refunded_commission", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("payment_id", "provider_user_id", name="uq_payment_allocation_provider"),
        sa.CheckConstraint("gross_amount > 0", name="ck_allocation_gross_positive"),
    )
    op.create_index("ix_payment_allocations_payment_id", "payment_allocations", ["payment_id"])
    op.create_index("ix_payment_allocations_provider_user_id", "payment_allocations", ["provider_user_id"])


def downgrade():
    op.drop_index("ix_payment_allocations_provider_user_id", table_name="payment_allocations")
    op.drop_index("ix_payment_allocations_payment_id", table_name="payment_allocations")
    op.drop_table("payment_allocations")
    with op.batch_alter_table("payment_transactions") as batch:
        batch.alter_column("provider_user_id", existing_type=sa.Integer(), nullable=False)
