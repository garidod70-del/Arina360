"""Add verified payment transactions and a unified 5% commission ledger.

Revision ID: 0008_commission_ledger
Revises: 0007_unique_user_roles
"""
from alembic import op

from app.database import Base
from app import payment_models  # noqa: F401

revision = "0008_commission_ledger"
down_revision = "0007_unique_user_roles"
branch_labels = None
depends_on = None

TABLES = ["payment_transactions", "commission_ledger"]


def upgrade():
    # Match the prior ecosystem migration: fresh test/development databases may
    # already have metadata-created tables before Alembic runs.
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
