"""Add QPay Merchant V2 invoice records.

Revision ID: 0009_qpay_invoices
Revises: 0008_commission_ledger
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_qpay_invoices"
down_revision = "0008_commission_ledger"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "qpay_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_type", sa.String(60), nullable=False),
        sa.Column("order_id", sa.String(100), nullable=False),
        sa.Column("qpay_invoice_id", sa.String(160), nullable=False),
        sa.Column("sender_invoice_no", sa.String(120), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MNT"),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("qr_text", sa.Text(), nullable=True),
        sa.Column("qr_image", sa.Text(), nullable=True),
        sa.Column("short_url", sa.Text(), nullable=True),
        sa.Column("bank_links_json", sa.Text(), nullable=True),
        sa.Column("allocations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("qpay_payment_id", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("qpay_invoice_id", name="uq_qpay_invoice_external_id"),
        sa.UniqueConstraint("sender_invoice_no", name="uq_qpay_sender_invoice_no"),
        sa.CheckConstraint("amount > 0", name="ck_qpay_invoice_amount_positive"),
    )
    for column in ("user_id", "order_type", "order_id", "status", "qpay_payment_id"):
        op.create_index(f"ix_qpay_invoices_{column}", "qpay_invoices", [column])


def downgrade():
    for column in ("user_id", "order_type", "order_id", "status", "qpay_payment_id"):
        op.drop_index(f"ix_qpay_invoices_{column}", table_name="qpay_invoices")
    op.drop_table("qpay_invoices")
