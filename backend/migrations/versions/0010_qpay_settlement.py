"""Add provider-level commission allocations.

Revision ID: 0010_qpay_settlement
Revises: 0009_qpay_invoices
"""
from alembic import op
import sqlalchemy as sa

from app.database import Base
from app import payment_models  # noqa: F401

revision = "0010_qpay_settlement"
down_revision = "0009_qpay_invoices"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"]: c for c in inspector.get_columns("payment_transactions")}
    if not columns["provider_user_id"].get("nullable", False):
        with op.batch_alter_table("payment_transactions") as batch:
            batch.alter_column("provider_user_id", existing_type=sa.Integer(), nullable=True)
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables["payment_allocations"]],
        checkfirst=True,
    )


def downgrade():
    Base.metadata.drop_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables["payment_allocations"]],
        checkfirst=True,
    )
    with op.batch_alter_table("payment_transactions") as batch:
        batch.alter_column("provider_user_id", existing_type=sa.Integer(), nullable=False)
