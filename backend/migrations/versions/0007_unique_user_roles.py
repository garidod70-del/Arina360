"""Prevent duplicate role assignments for the same user.

Revision ID: 0007_unique_user_roles
Revises: 0006_ecosystem
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_unique_user_roles"
down_revision = "0006_ecosystem"
branch_labels = None
depends_on = None


def upgrade():
    # Duplicate copies of the same role do not carry separate meaning. Keep
    # the oldest assignment before enforcing the invariant.
    op.execute(sa.text("""
        DELETE FROM user_roles
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM user_roles
            GROUP BY user_id, role
        )
    """))
    existing = inspect(op.get_bind()).get_unique_constraints("user_roles")
    if not any(item.get("name") == "uq_user_role" for item in existing):
        with op.batch_alter_table("user_roles") as batch_op:
            batch_op.create_unique_constraint(
                "uq_user_role",
                ["user_id", "role"],
            )


def downgrade():
    existing = inspect(op.get_bind()).get_unique_constraints("user_roles")
    if any(item.get("name") == "uq_user_role" for item in existing):
        with op.batch_alter_table("user_roles") as batch_op:
            batch_op.drop_constraint("uq_user_role", type_="unique")
