"""Add venue availability slots and booking workflow."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_venue_booking_slots"
down_revision = "0003_service_marketplace"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(inspect(op.get_bind()).get_table_names())
    if "venue_slots" not in existing:
        op.create_table(
            "venue_slots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("venue_name", sa.String(160), nullable=False),
            sa.Column("venue_address", sa.String(240), nullable=False),
            sa.Column("sport", sa.String(80), nullable=False),
            sa.Column("booking_date", sa.Date(), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="available"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("provider_user_id", "venue_name", "booking_date", "start_time", name="uq_venue_slot_start"),
        )
        op.create_index("ix_venue_slots_provider_user_id", "venue_slots", ["provider_user_id"])
        op.create_index("ix_venue_slots_sport", "venue_slots", ["sport"])
        op.create_index("ix_venue_slots_booking_date", "venue_slots", ["booking_date"])
        op.create_index("ix_venue_slots_status", "venue_slots", ["status"])
    if "venue_bookings" not in existing:
        op.create_table(
            "venue_bookings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slot_id", sa.Integer(), sa.ForeignKey("venue_slots.id", ondelete="CASCADE"), nullable=False),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("contact_phone", sa.String(24), nullable=False),
            sa.Column("purpose", sa.String(500), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_venue_bookings_slot_id", "venue_bookings", ["slot_id"])
        op.create_index("ix_venue_bookings_customer_id", "venue_bookings", ["customer_id"])
        op.create_index("ix_venue_bookings_provider_user_id", "venue_bookings", ["provider_user_id"])
        op.create_index("ix_venue_bookings_status", "venue_bookings", ["status"])


def downgrade():
    op.drop_table("venue_bookings")
    op.drop_table("venue_slots")
