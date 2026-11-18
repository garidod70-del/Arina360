"""Add QPay Merchant V2 invoice records.

Revision ID: 0009_qpay_invoices
Revises: 0008_commission_ledger
"""
from alembic import op

from app.database import Base
from app import qpay_models  # noqa: F401

revision = "0009_qpay_invoices"
down_revision = "0008_commission_ledger"
branch_labels = None
depends_on = None

TABLES = ["qpay_invoices"]


def upgrade():
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables[name] for name in TABLES],
        checkfirst=True,
    )


def downgrade():
    Base.metadata.drop_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables[name] for name in reversed(TABLES)],
        checkfirst=True,
    )
