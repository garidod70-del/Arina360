from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("provider", "external_payment_id", name="uq_payment_provider_external_id"),
        CheckConstraint("gross_amount > 0", name="ck_payment_gross_positive"),
        CheckConstraint("refunded_amount >= 0 AND refunded_amount <= gross_amount", name="ck_payment_refund_bounds"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    external_payment_id: Mapped[str] = mapped_column(String(160), nullable=False)
    order_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    buyer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    provider_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    gross_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_net_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    refunded_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refunded_commission: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="paid", index=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class CommissionLedger(Base):
    __tablename__ = "commission_ledger"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_commission_ledger_event_key"),
        CheckConstraint("gross_delta >= 0 AND commission_delta >= 0", name="ck_commission_ledger_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payment_transactions.id", ondelete="RESTRICT"), nullable=False, index=True)
    event_key: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    gross_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_net_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
