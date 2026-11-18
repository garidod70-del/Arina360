from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class QPayInvoice(Base):
    __tablename__ = "qpay_invoices"
    __table_args__ = (
        UniqueConstraint("qpay_invoice_id", name="uq_qpay_invoice_external_id"),
        UniqueConstraint("sender_invoice_no", name="uq_qpay_sender_invoice_no"),
        CheckConstraint("amount > 0", name="ck_qpay_invoice_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    qpay_invoice_id: Mapped[str] = mapped_column(String(160), nullable=False)
    sender_invoice_no: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MNT")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    qr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    allocations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    qpay_payment_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
