"""Add shared service provider and request tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_service_marketplace"
down_revision = "0002_referee_licence"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    if "service_providers" not in existing_tables:
        op.create_table(
            "service_providers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("category", sa.String(length=60), nullable=False),
            sa.Column("display_name", sa.String(length=140), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("sport", sa.String(length=80), nullable=True),
            sa.Column("region", sa.String(length=120), nullable=False),
            sa.Column("price_from", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("credentials", sa.String(length=240), nullable=True),
            sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("verification_note", sa.Text(), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_service_providers_user_id", "service_providers", ["user_id"], unique=True)
        op.create_index("ix_service_providers_category", "service_providers", ["category"])
        op.create_index("ix_service_providers_sport", "service_providers", ["sport"])
        op.create_index("ix_service_providers_region", "service_providers", ["region"])
        op.create_index("ix_service_providers_verification_status", "service_providers", ["verification_status"])

    if "service_requests" not in existing_tables:
        op.create_table(
            "service_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("category", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("details", sa.Text(), nullable=False),
            sa.Column("sport", sa.String(length=80), nullable=True),
            sa.Column("region", sa.String(length=120), nullable=False),
            sa.Column("preferred_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("contact_phone", sa.String(length=24), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
            sa.Column("response_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_service_requests_requester_id", "service_requests", ["requester_id"])
        op.create_index("ix_service_requests_provider_user_id", "service_requests", ["provider_user_id"])
        op.create_index("ix_service_requests_category", "service_requests", ["category"])
        op.create_index("ix_service_requests_status", "service_requests", ["status"])


def downgrade():
    # Preserve service request history if a rollback is needed.
    pass
