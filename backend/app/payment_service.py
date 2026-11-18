from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.payment_models import CommissionLedger, PaymentAllocation, PaymentTransaction

COMMISSION_RATE_BPS = 500


def commission_for(amount: int) -> int:
    """5% commission, rounded down to the nearest whole MNT."""
    if amount < 0:
        raise ValueError("amount must not be negative")
    return (amount * COMMISSION_RATE_BPS) // 10_000


def record_payment(
    db: Session, *, provider: str, external_payment_id: str, order_type: str,
    order_id: str, category: str, buyer_user_id: int, provider_user_id: int | None,
    amount: int, allocations: list[dict] | None = None,
) -> tuple[PaymentTransaction, bool]:
    if amount <= 0 or amount > 2_000_000_000:
        raise HTTPException(status_code=422, detail="Төлбөрийн дүн буруу байна.")
    existing = db.query(PaymentTransaction).filter_by(
        provider=provider, external_payment_id=external_payment_id
    ).with_for_update().first()
    if existing:
        same = (
            existing.gross_amount == amount and existing.order_type == order_type
            and existing.order_id == order_id and existing.buyer_user_id == buyer_user_id
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

    normalized = allocations or ([{"provider_user_id": provider_user_id, "gross_amount": amount}] if provider_user_id else [])
    normalized = [x for x in normalized if x.get("provider_user_id") and int(x.get("gross_amount", 0)) > 0]
    if sum(int(x["gross_amount"]) for x in normalized) != amount:
        raise HTTPException(status_code=422, detail="Үйлчилгээ үзүүлэгчийн орлогын хуваарилалт төлбөрийн дүнтэй таарахгүй байна.")

    # Allocate the invoice-level commission exactly; last provider receives rounding remainder.
    remaining_commission = commission
    remaining_gross = amount
    for index, allocation in enumerate(normalized):
        gross = int(allocation["gross_amount"])
        if index == len(normalized) - 1:
            allocated_commission = remaining_commission
        else:
            allocated_commission = (commission * gross) // amount
            remaining_commission -= allocated_commission
            remaining_gross -= gross
        db.add(PaymentAllocation(
            payment_id=payment.id, provider_user_id=int(allocation["provider_user_id"]),
            gross_amount=gross, commission_amount=allocated_commission,
            provider_net_amount=gross - allocated_commission,
        ))
    db.add(CommissionLedger(
        payment_id=payment.id, event_key=f"paid:{provider}:{external_payment_id}",
        event_type="paid", gross_delta=amount, commission_delta=commission,
        provider_net_delta=amount - commission,
    ))
    db.flush()
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

    new_total_refund = payment.refunded_amount + refund_amount
    allocations = db.query(PaymentAllocation).filter_by(payment_id=payment.id).order_by(PaymentAllocation.id).all()
    # Allocate every refunded tugrik across providers without losing rounding remainder.
    targets = []
    allocated_refund = 0
    for allocation in allocations:
        target = allocation.gross_amount if new_total_refund == payment.gross_amount else (
            allocation.gross_amount * new_total_refund
        ) // payment.gross_amount
        targets.append(target)
        allocated_refund += target - allocation.refunded_amount
    remainder = refund_amount - allocated_refund
    for index, allocation in enumerate(allocations):
        if remainder <= 0:
            break
        if targets[index] < allocation.gross_amount:
            targets[index] += 1
            remainder -= 1

    target_total_commission = payment.commission_amount if new_total_refund == payment.gross_amount else (
        payment.commission_amount * new_total_refund
    ) // payment.gross_amount
    commission_targets = []
    commission_allocated = 0
    for allocation in allocations:
        target = allocation.commission_amount if new_total_refund == payment.gross_amount else (
            allocation.commission_amount * new_total_refund // payment.gross_amount
        )
        commission_targets.append(target)
        commission_allocated += target
    commission_remainder = target_total_commission - commission_allocated
    if commission_targets and commission_remainder:
        commission_targets[-1] += commission_remainder

    commission_reversal = 0
    provider_net_reversal = 0
    for index, allocation in enumerate(allocations):
        refund_delta = targets[index] - allocation.refunded_amount
        commission_delta = commission_targets[index] - allocation.refunded_commission
        allocation.refunded_amount = targets[index]
        allocation.refunded_commission = commission_targets[index]
        commission_reversal += commission_delta
        provider_net_reversal += refund_delta - commission_delta

    payment.refunded_amount = new_total_refund
    payment.refunded_commission += commission_reversal
    payment.status = "refunded" if new_total_refund == payment.gross_amount else "partially_refunded"
    db.add(CommissionLedger(
        payment_id=payment.id, event_key=event_key, event_type="refund",
        gross_delta=refund_amount, commission_delta=commission_reversal,
        provider_net_delta=provider_net_reversal,
    ))
    db.flush()
    return payment, True
