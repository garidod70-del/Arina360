"""Add referee licence metadata and verification audit."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0002_referee_licence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("referee_profiles")}
    if "license_number" not in columns:
        op.add_column("referee_profiles", sa.Column("license_number", sa.String(length=120), nullable=True))
        op.create_index("ix_referee_profiles_license_number", "referee_profiles", ["license_number"])
    if "license_issuer" not in columns:
        op.add_column("referee_profiles", sa.Column("license_issuer", sa.String(length=160), nullable=True))
    if "license_expires_at" not in columns:
        op.add_column("referee_profiles", sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True))
    if "verified_at" not in columns:
        op.add_column("referee_profiles", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    if "verified_by" not in columns:
        op.add_column("referee_profiles", sa.Column("verified_by", sa.Integer(), nullable=True))
    if "verification_note" not in columns:
        op.add_column("referee_profiles", sa.Column("verification_note", sa.Text(), nullable=True))


def downgrade():
    # Keep licensing evidence and audit history during rollback.
    pass
