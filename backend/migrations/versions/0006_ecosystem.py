"""Add ARENA 360 ecosystem tables.

Revision ID: 0006_ecosystem
Revises: 0005_competitions
"""
from alembic import op

from app.database import Base
from app import ecosystem_models  # noqa: F401

revision = "0006_ecosystem"
down_revision = "0005_competitions"
branch_labels = None
depends_on = None

TABLES = [
    "clubs", "club_memberships", "coach_profiles", "products", "cart_items",
    "shop_orders", "shop_order_items", "notifications", "conversations",
    "chat_messages", "qr_passes", "medal_awards",
]


def upgrade():
    # Safe for fresh deployments where create_all may have run before Alembic.
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
