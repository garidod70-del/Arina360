"""Add payment states to all priced order types and club membership fees.

Revision ID: 0011_order_payment_states
Revises: 0010_qpay_settlement
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_order_payment_states"
down_revision = "0010_qpay_settlement"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clubs", sa.Column("membership_fee", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("club_memberships", sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"))
    op.add_column("shop_orders", sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"))
    op.add_column("referee_bookings", sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"))
    op.add_column("service_requests", sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"))
    op.add_column("venue_bookings", sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"))
    for table in ("club_memberships", "shop_orders", "referee_bookings", "service_requests", "venue_bookings"):
        op.create_index(f"ix_{table}_payment_status", table, ["payment_status"])


def downgrade():
    for table in ("club_memberships", "shop_orders", "referee_bookings", "service_requests", "venue_bookings"):
        op.drop_index(f"ix_{table}_payment_status", table_name=table)
    op.drop_column("venue_bookings", "payment_status")
    op.drop_column("service_requests", "payment_status")
    op.drop_column("referee_bookings", "payment_status")
    op.drop_column("shop_orders", "payment_status")
    op.drop_column("club_memberships", "payment_status")
    op.drop_column("clubs", "membership_fee")
