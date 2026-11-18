"""Allow referee bookings without a contact phone.

Revision ID: 0012_referee_phone_optional
Revises: 0011_order_payment_states
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_referee_phone_optional"
down_revision = "0011_order_payment_states"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("referee_bookings") as batch:
        batch.alter_column("contact_phone", existing_type=sa.String(length=24), nullable=True)


def downgrade():
    with op.batch_alter_table("referee_bookings") as batch:
        batch.alter_column("contact_phone", existing_type=sa.String(length=24), nullable=False)
