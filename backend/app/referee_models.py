from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class RefereeProfile(Base):
    __tablename__ = "referee_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    sport: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    rank: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(120), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    license_issuer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    license_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RefereeBooking(Base):
    __tablename__ = "referee_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sport: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    rank: Mapped[str] = mapped_column(String(80), nullable=False)
    booking_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    venue: Mapped[str] = mapped_column(String(240), nullable=False)
    referee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(40), nullable=False)
    unit_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    work_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    transport_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    food_fee: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False, index=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class RefereeRating(Base):
    __tablename__ = "referee_ratings"
    __table_args__ = (UniqueConstraint("booking_id", "rater_id", name="uq_referee_rating_booking_rater"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("referee_bookings.id", ondelete="CASCADE"), index=True)
    referee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rater_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
