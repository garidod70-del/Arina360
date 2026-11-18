"""Add tournament registration, draws and match results."""

from alembic import op
import sqlalchemy as sa

revision = "0005_competitions"
down_revision = "0004_venue_booking_slots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("sport", sa.String(80), nullable=False),
        sa.Column("format", sa.String(32), nullable=False, server_default="single_elimination"),
        sa.Column("region", sa.String(120), nullable=False),
        sa.Column("venue", sa.String(200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_participants", sa.Integer(), nullable=False, server_default="64"),
        sa.Column("age_group", sa.String(80), nullable=True),
        sa.Column("weight_class", sa.String(80), nullable=True),
        sa.Column("rules", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="registration_open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tournaments_organizer_id", "tournaments", ["organizer_id"])
    op.create_index("ix_tournaments_sport", "tournaments", ["sport"])
    op.create_index("ix_tournaments_region", "tournaments", ["region"])
    op.create_index("ix_tournaments_starts_at", "tournaments", ["starts_at"])
    op.create_index("ix_tournaments_status", "tournaments", ["status"])

    op.create_table(
        "tournament_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("club_name", sa.String(120), nullable=True),
        sa.Column("contact_phone", sa.String(24), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="registered"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tournament_id", "contact_phone", name="uq_tournament_participant_phone"),
    )
    op.create_index("ix_tournament_participants_tournament_id", "tournament_participants", ["tournament_id"])
    op.create_index("ix_tournament_participants_user_id", "tournament_participants", ["user_id"])

    op.create_table(
        "tournament_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("match_number", sa.Integer(), nullable=False),
        sa.Column("stage_name", sa.String(80), nullable=False),
        sa.Column("participant1_id", sa.Integer(), sa.ForeignKey("tournament_participants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("participant2_id", sa.Integer(), sa.ForeignKey("tournament_participants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("tournament_participants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("score1", sa.Integer(), nullable=True),
        sa.Column("score2", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mat_name", sa.String(80), nullable=True),
        sa.Column("next_match_id", sa.Integer(), sa.ForeignKey("tournament_matches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("next_slot", sa.String(2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tournament_id", "round_number", "match_number", name="uq_tournament_round_match"),
    )
    op.create_index("ix_tournament_matches_tournament_id", "tournament_matches", ["tournament_id"])
    op.create_index("ix_tournament_matches_status", "tournament_matches", ["status"])


def downgrade():
    op.drop_table("tournament_matches")
    op.drop_table("tournament_participants")
    op.drop_table("tournaments")
