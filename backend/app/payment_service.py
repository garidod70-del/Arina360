from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.payment_models import CommissionLedger, PaymentTransaction

COMMISSION_RATE_BPS = 500


def commission_for(amount: int) -> int:
    """5% commission, rounded down to the nearest whole MNT."""
    if amount < 0:
        raise ValueError("amount must not be negative")
    return (amount * COMMISSION_RATE_BPS) // 10_000


def record_payment(
    db: Session, *, provider: str, external_payment_id: str, order_type: str,
    order_id: str, category: str, buyer_user_id: int, provider_user_id: int,
    amount: int,
) -> tuple[PaymentTransaction, bool]:
    if amount <= 0 or amount > 2_000_000_000:
        raise HTTPException(status_code=422, detail="Төлбөрийн дүн буруу байна.")
    existing = db.query(PaymentTransaction).filter_by(
        provider=provider, external_payment_id=external_payment_id
    ).with_for_update().first()
    if existing:
        same = (
            existing.gross_amount == amount and existing.order_type == order_type
            and existing.order_id == order_id and existing.provider_user_id == provider_user_id
            and existing.buyer_user_id == buyer_user_id
        )
        if not same:
            raise HTTPException(status_code=409, detail="Гүйлгээний ID өмнөх өөр мэдээлэлтэй давхцаж байна.")
        return existing, False

    commission = commission_for(amount)
    payment = PaymentTransaction(
        provider=provider, external_payment_id=external_payment_id,
        order_type=order_type, order_id=order_id, category=category,
        buyer_user_id=buyer_user_id, provider_user_id=provider_user_id,
        gross_amount=amount, commission_rate_bps=COMMISSION_RATE_BPS,
        commission_amount=commission, provider_net_amount=amount - commission,
        status="paid",
    )
    db.add(payment)
    db.flush()
    db.add(CommissionLedger(
        payment_id=payment.id, event_key=f"paid:{provider}:{external_payment_id}",
        event_type="paid", gross_delta=amount, commission_delta=commission,
        provider_net_delta=amount - commission,
    ))
    return payment, True


def record_refund(db: Session, *, provider: str, external_payment_id: str,
                  external_event_id: str, refund_amount: int) -> tuple[PaymentTransaction, bool]:
    payment = db.query(PaymentTransaction).filter_by(
        provider=provider, external_payment_id=external_payment_id
    ).with_for_update().first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Төлбөрийн гүйлгээ олдсонгүй.")
    event_key = f"refund:{provider}:{external_event_id}"
    if db.query(CommissionLedger.id).filter_by(event_key=event_key).first():
        return payment, False
    if refund_amount <= 0 or payment.refunded_amount + refund_amount > payment.gross_amount:
        raise HTTPException(status_code=422, detail="Буцаалтын дүн төлсөн дүнгээс хэтэрч болохгүй.")

    old_refund = payment.refunded_amount
    new_refund = old_refund + refund_amount
    # Reverse the cumulative commission proportionally; this avoids rounding drift
    # when one payment is refunded in several partial refunds.
    target_reversed = (payment.commission_amount * new_refund) // payment.gross_amount
    commission_reversal = target_reversed - payment.refunded_commission
    provider_net_reversal = refund_amount - commission_reversal
    payment.refunded_amount = new_refund
    payment.refunded_commission += commission_reversal
    payment.status = "refunded" if new_refund == payment.gross_amount else "partially_refunded"
    db.add(CommissionLedger(
        payment_id=payment.id, event_key=event_key, event_type="refund",
        gross_delta=refund_amount, commission_delta=commission_reversal,
        provider_net_delta=provider_net_reversal,
    ))
    return payment, True
