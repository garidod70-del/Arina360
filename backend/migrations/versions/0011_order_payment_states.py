"""Add payment states to priced order types and club membership fees.

Revision ID: 0011_order_payment_states
Revises: 0010_qpay_settlement
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_order_payment_states"
down_revision = "0010_qpay_settlement"
branch_labels = None
depends_on = None

COLUMNS = {
    "clubs": ("membership_fee", sa.Integer(), "0"),
    "club_memberships": ("payment_status", sa.String(20), "unpaid"),
    "shop_orders": ("payment_status", sa.String(20), "unpaid"),
    "referee_bookings": ("payment_status", sa.String(20), "unpaid"),
    "service_requests": ("payment_status", sa.String(20), "unpaid"),
    "venue_bookings": ("payment_status", sa.String(20), "unpaid"),
}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, (column, column_type, default) in COLUMNS.items():
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column not in existing:
            op.add_column(table, sa.Column(column, column_type, nullable=False, server_default=default))
    inspector = sa.inspect(bind)
    for table in ("club_memberships", "shop_orders", "referee_bookings", "service_requests", "venue_bookings"):
        index_name = f"ix_{table}_payment_status"
        indexes = {idx["name"] for idx in inspector.get_indexes(table)}
        if index_name not in indexes:
            op.create_index(index_name, table, ["payment_status"])


def downgrade():
    for table in ("club_memberships", "shop_orders", "referee_bookings", "service_requests", "venue_bookings"):
        op.drop_index(f"ix_{table}_payment_status", table_name=table)
    for table, (column, _, _) in reversed(list(COLUMNS.items())):
        op.drop_column(table, column)
