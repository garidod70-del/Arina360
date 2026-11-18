import uuid

from app.database import SessionLocal
from app.models import User
from app.payment_models import CommissionLedger, PaymentAllocation, PaymentTransaction
from app.payment_service import commission_for, record_payment, record_refund


def test_five_percent_commission_uses_integer_mnt_rounding():
    assert commission_for(10_000) == 500
    assert commission_for(50_000) == 2_500
    assert commission_for(100_000) == 5_000
    assert commission_for(1_000_000) == 50_000
    assert commission_for(19) == 0


def test_payment_is_idempotent_and_partial_refunds_reverse_commission_proportionally():
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:12]
    buyer = User(phone=f"+976{suffix}01", password_hash="test")
    provider = User(phone=f"+976{suffix}02", password_hash="test")
    db.add_all([buyer, provider])
    db.flush()
    payment_id = None
    try:
        payment, created = record_payment(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            order_type="store_order", order_id=f"order-{suffix}",
            category="sports_store", buyer_user_id=buyer.id,
            provider_user_id=provider.id, amount=100_000,
            allocations=[{"provider_user_id": provider.id, "gross_amount": 100_000}],
        )
        assert created is True
        payment_id = payment.id
        assert payment.commission_amount == 5_000
        assert payment.provider_net_amount == 95_000

        duplicate, duplicate_created = record_payment(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            order_type="store_order", order_id=f"order-{suffix}",
            category="sports_store", buyer_user_id=buyer.id,
            provider_user_id=provider.id, amount=100_000,
            allocations=[{"provider_user_id": provider.id, "gross_amount": 100_000}],
        )
        assert duplicate.id == payment.id
        assert duplicate_created is False
        db.flush()

        partial, partial_created = record_refund(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            external_event_id=f"refund-part-{suffix}", refund_amount=20_000,
        )
        assert partial_created is True
        allocation = db.query(PaymentAllocation).filter_by(payment_id=payment.id).one()
        assert partial.refunded_amount == 20_000
        assert partial.refunded_commission == 1_000
        assert allocation.refunded_amount == 20_000
        assert allocation.refunded_commission == 1_000
        assert partial.status == "partially_refunded"

        repeated, repeated_created = record_refund(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            external_event_id=f"refund-part-{suffix}", refund_amount=20_000,
        )
        assert repeated.id == payment.id
        assert repeated_created is False
        db.flush()

        final, final_created = record_refund(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            external_event_id=f"refund-rest-{suffix}", refund_amount=80_000,
        )
        assert final_created is True
        assert final.refunded_amount == 100_000
        assert final.refunded_commission == 5_000
        assert final.status == "refunded"
        assert allocation.refunded_amount == 100_000
        assert allocation.refunded_commission == 5_000
        db.commit()
    finally:
        if payment_id is not None:
            db.query(CommissionLedger).filter_by(payment_id=payment_id).delete()
            db.query(PaymentAllocation).filter_by(payment_id=payment_id).delete()
            db.query(PaymentTransaction).filter_by(id=payment_id).delete()
        db.query(User).filter(User.id.in_([buyer.id, provider.id])).delete(synchronize_session=False)
        db.commit()
        db.close()
