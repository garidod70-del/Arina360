from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    sport: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="single_elimination")
    region: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    age_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    weight_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="registration_open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"
    __table_args__ = (
        UniqueConstraint("tournament_id", "contact_phone", name="uq_tournament_participant_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    club_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(24), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="registered")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TournamentMatch(Base):
    __tablename__ = "tournament_matches"
    __table_args__ = (
        UniqueConstraint("tournament_id", "round_number", "match_number", name="uq_tournament_round_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    match_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_name: Mapped[str] = mapped_column(String(80), nullable=False)
    participant1_id: Mapped[int | None] = mapped_column(ForeignKey("tournament_participants.id", ondelete="SET NULL"), nullable=True)
    participant2_id: Mapped[int | None] = mapped_column(ForeignKey("tournament_participants.id", ondelete="SET NULL"), nullable=True)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("tournament_participants.id", ondelete="SET NULL"), nullable=True)
    score1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mat_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    next_match_id: Mapped[int | None] = mapped_column(ForeignKey("tournament_matches.id", ondelete="SET NULL"), nullable=True)
    next_slot: Mapped[str | None] = mapped_column(String(2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
