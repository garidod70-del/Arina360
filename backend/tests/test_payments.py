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
        db.commit()

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


def test_qpay_store_checkout_uses_registered_phone_and_splits_five_percent(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import payments as payment_router

    def register(client, phone):
        response = client.post("/api/v1/auth/register", json={
            "phone": phone, "password": "secure-test-password",
        })
        assert response.status_code == 201, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    with TestClient(app) as client:
        suffix = uuid.uuid4().hex[:8]
        buyer_phone = f"+97678{suffix}"
        buyer_headers = register(client, buyer_phone)
        seller_headers = register(client, f"+97679{suffix}")

        product = client.post("/api/v1/store/products", headers=seller_headers, json={
            "title": "Тест спорт бараа", "description": "Төлбөрийн урсгалын тест",
            "category": "training", "price": 50_000, "stock": 2,
        })
        assert product.status_code == 201, product.text
        cart = client.post("/api/v1/store/cart", headers=buyer_headers, json={
            "product_id": product.json()["id"], "quantity": 1,
        })
        assert cart.status_code == 200, cart.text
        order = client.post("/api/v1/store/checkout", headers=buyer_headers, json={
            "delivery_address": "Улаанбаатар хот, туршилтын хаяг",
        })
        assert order.status_code == 201, order.text

        monkeypatch.setattr(payment_router, "get_settings", lambda: SimpleNamespace(
            qpay_callback_url="https://api.example.test",
        ))
        monkeypatch.setattr(payment_router, "create_invoice", lambda **kwargs: {
            "invoice_id": "qpay-" + uuid.uuid4().hex,
            "qr_text": "qpay-test-qr",
            "qr_image": "",
            "qPay_shortUrl": "https://qpay.mn/test",
            "urls": [],
        })
        invoice = client.post("/api/v1/payments/qpay/invoice", headers=buyer_headers, json={
            "order_type": "store_order", "order_id": order.json()["id"],
        })
        assert invoice.status_code == 201, invoice.text
        assert invoice.json()["amount"] == 50_000

        payment_id = "payment-" + uuid.uuid4().hex
        monkeypatch.setattr(payment_router, "check_invoice", lambda _invoice_id: {
            "paid_amount": "50000.00",
            "rows": [{
                "payment_id": payment_id, "payment_status": "PAID",
                "payment_amount": "50000.00", "payment_currency": "MNT",
            }],
        })
        confirmed = client.post(
            f"/api/v1/payments/qpay/invoices/{invoice.json()['id']}/check",
            headers=buyer_headers, json={},
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["status"] == "paid"

        with SessionLocal() as db:
            stored = db.query(PaymentTransaction).filter_by(
                provider="qpay", order_id=str(order.json()["id"]),
            ).one()
            assert stored.gross_amount == 50_000
            assert stored.commission_amount == 2_500
            assert stored.provider_net_amount == 47_500
            from app.ecosystem_models import ShopOrder
            paid_order = db.get(ShopOrder, order.json()["id"])
            assert paid_order.payment_status == "paid"
            assert paid_order.contact_phone == buyer_phone

        notifications = client.get("/api/v1/notifications", headers=seller_headers)
        assert notifications.status_code == 200
        order_notifications = [x for x in notifications.json() if x["category"] == "order"]
        assert order_notifications
        assert any(buyer_phone in x["body"] for x in order_notifications)
