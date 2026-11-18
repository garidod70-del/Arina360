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
    suffix = uuid.uuid4().hex[:12]
    buyer_id = provider_id = payment_id = None
    db = SessionLocal()
    try:
        buyer = User(phone=f"+976{suffix}01", password_hash="test")
        provider = User(phone=f"+976{suffix}02", password_hash="test")
        db.add_all([buyer, provider])
        db.flush()
        buyer_id, provider_id = buyer.id, provider.id
        payment, created = record_payment(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            order_type="store_order", order_id=f"order-{suffix}",
            category="sports_store", buyer_user_id=buyer_id,
            provider_user_id=provider_id, amount=100_000,
            allocations=[{"provider_user_id": provider_id, "gross_amount": 100_000}],
        )
        assert created is True
        payment_id = payment.id
        assert payment.commission_amount == 5_000
        assert payment.provider_net_amount == 95_000
        db.commit()
    finally:
        db.close()

    # Re-open a fresh session to prove settlement/refund records survive commits.
    db = SessionLocal()
    try:
        payment = db.get(PaymentTransaction, payment_id)
        assert payment is not None
        duplicate, duplicate_created = record_payment(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            order_type="store_order", order_id=f"order-{suffix}",
            category="sports_store", buyer_user_id=buyer_id,
            provider_user_id=provider_id, amount=100_000,
            allocations=[{"provider_user_id": provider_id, "gross_amount": 100_000}],
        )
        assert duplicate.id == payment_id
        assert duplicate_created is False

        partial, partial_created = record_refund(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            external_event_id=f"refund-part-{suffix}", refund_amount=20_000,
        )
        assert partial_created is True
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        payment = db.get(PaymentTransaction, payment_id)
        allocation = db.query(PaymentAllocation).filter_by(payment_id=payment_id).one()
        assert payment.refunded_amount == 20_000
        assert payment.refunded_commission == 1_000
        assert allocation.refunded_amount == 20_000
        assert allocation.refunded_commission == 1_000
        assert payment.status == "partially_refunded"

        repeated, repeated_created = record_refund(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            external_event_id=f"refund-part-{suffix}", refund_amount=20_000,
        )
        assert repeated.id == payment_id
        assert repeated_created is False
        final, final_created = record_refund(
            db, provider="qpay", external_payment_id=f"invoice-{suffix}",
            external_event_id=f"refund-rest-{suffix}", refund_amount=80_000,
        )
        assert final_created is True
        db.commit()
        assert final.refunded_amount == 100_000
        assert final.refunded_commission == 5_000
        assert final.status == "refunded"
        assert allocation.refunded_amount == 100_000
        assert allocation.refunded_commission == 5_000
    finally:
        if payment_id is not None:
            db.query(CommissionLedger).filter_by(payment_id=payment_id).delete()
            db.query(PaymentAllocation).filter_by(payment_id=payment_id).delete()
            db.query(PaymentTransaction).filter_by(id=payment_id).delete()
        if buyer_id is not None and provider_id is not None:
            db.query(User).filter(User.id.in_([buyer_id, provider_id])).delete(synchronize_session=False)
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
        suffix = str(uuid.uuid4().int % 100000000).zfill(8)
        buyer_phone = f"+97678{suffix}"
        buyer_headers = register(client, buyer_phone)
        seller_headers = register(client, f"+97679{suffix}")
        admin_phone = f"+97670{suffix}"
        admin_headers = register(client, admin_phone)
        from app.models import UserRole
        with SessionLocal() as db:
            admin_user = db.query(User).filter_by(phone=admin_phone).one()
            db.add(UserRole(user_id=admin_user.id, role="admin"))
            db.commit()

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

        monkeypatch.setattr(payment_router, "refund_payment", lambda _payment_id: {})
        refunded = client.post(
            f"/api/v1/payments/qpay/invoices/{invoice.json()['id']}/refund",
            headers=admin_headers, json={},
        )
        assert refunded.status_code == 200, refunded.text
        assert refunded.json()["status"] == "refunded"
        assert refunded.json()["refund_amount"] == 50_000
        assert refunded.json()["commission_reversed"] == 2_500

        from app.ecosystem_models import ShopOrder
        from app.qpay_models import QPayInvoice
        with SessionLocal() as db:
            settled = db.query(PaymentTransaction).filter_by(
                provider="qpay", order_id=str(order.json()["id"]),
            ).one()
            stored_order = db.get(ShopOrder, order.json()["id"])
            stored_invoice = db.get(QPayInvoice, invoice.json()["id"])
            assert settled.refunded_amount == 50_000
            assert settled.refunded_commission == 2_500
            assert settled.status == "refunded"
            assert stored_order.payment_status == "refunded"
            assert stored_invoice.status == "refunded"


def test_multi_seller_store_payment_splits_commission_once_and_notifies_once(monkeypatch):
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
        suffix = str(uuid.uuid4().int % 100000000).zfill(8)
        buyer_phone = f"+97677{suffix}"
        buyer_headers = register(client, buyer_phone)
        seller_a_headers = register(client, f"+97676{suffix}")
        seller_b_headers = register(client, f"+97675{suffix}")

        products = []
        for headers, title, price in (
            (seller_a_headers, "Тест бараа A", 40_000),
            (seller_b_headers, "Тест бараа B", 60_000),
        ):
            response = client.post("/api/v1/store/products", headers=headers, json={
                "title": title, "description": "Олон худалдагчийн төлбөрийн тест",
                "category": "training", "price": price, "stock": 2,
            })
            assert response.status_code == 201, response.text
            products.append(response.json()["id"])

        for product_id in products:
            response = client.post("/api/v1/store/cart", headers=buyer_headers, json={
                "product_id": product_id, "quantity": 1,
            })
            assert response.status_code == 200, response.text

        order = client.post("/api/v1/store/checkout", headers=buyer_headers, json={
            "delivery_address": "Улаанбаатар хот, олон худалдагчийн тест",
        })
        assert order.status_code == 201, order.text
        assert order.json()["total_amount"] == 100_000

        monkeypatch.setattr(payment_router, "get_settings", lambda: SimpleNamespace(
            qpay_callback_url="https://api.example.test",
        ))
        invoice_id = "qpay-" + uuid.uuid4().hex
        monkeypatch.setattr(payment_router, "create_invoice", lambda **kwargs: {
            "invoice_id": invoice_id, "qr_text": "qpay-test-qr",
            "qr_image": "", "qPay_shortUrl": "https://qpay.mn/test", "urls": [],
        })
        invoice = client.post("/api/v1/payments/qpay/invoice", headers=buyer_headers, json={
            "order_type": "store_order", "order_id": order.json()["id"],
        })
        assert invoice.status_code == 201, invoice.text

        payment_ids = ["payment-" + uuid.uuid4().hex, "payment-" + uuid.uuid4().hex]
        monkeypatch.setattr(payment_router, "check_invoice", lambda _invoice_id: {
            "paid_amount": "100000.00",
            "rows": [
                {"payment_id": payment_ids[0], "payment_status": "PAID",
                 "payment_amount": "40000.00", "payment_currency": "MNT"},
                {"payment_id": payment_ids[1], "payment_status": "PAID",
                 "payment_amount": "60000.00", "payment_currency": "MNT"},
            ],
        })

        path = f"/api/v1/payments/qpay/invoices/{invoice.json()['id']}/check"
        first = client.post(path, headers=buyer_headers, json={})
        assert first.status_code == 200, first.text
        second = client.post(path, headers=buyer_headers, json={})
        assert second.status_code == 200, second.text
        assert second.json()["already_confirmed"] is True

        with SessionLocal() as db:
            payment = db.query(PaymentTransaction).filter_by(
                provider="qpay", external_payment_id=invoice_id,
            ).one()
            assert payment.gross_amount == 100_000
            assert payment.commission_amount == 5_000
            assert payment.provider_net_amount == 95_000
            allocations = db.query(PaymentAllocation).filter_by(
                payment_id=payment.id,
            ).order_by(PaymentAllocation.provider_user_id).all()
            assert len(allocations) == 2
            assert sum(x.gross_amount for x in allocations) == 100_000
            assert sum(x.commission_amount for x in allocations) == 5_000
            assert sum(x.provider_net_amount for x in allocations) == 95_000
            ledger_rows = db.query(CommissionLedger).filter_by(
                payment_id=payment.id, event_type="paid",
            ).all()
            assert len(ledger_rows) == 1

        for seller_headers in (seller_a_headers, seller_b_headers):
            notifications = client.get("/api/v1/notifications", headers=seller_headers)
            assert notifications.status_code == 200
            order_notifications = [
                item for item in notifications.json()
                if item["category"] == "order" and str(order.json()["id"]) in item["body"]
            ]
            assert len(order_notifications) == 1
            assert buyer_phone in order_notifications[0]["body"]


def test_pending_qpay_store_payment_does_not_notify_seller_or_create_commission(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import payments as payment_router
    from app.ecosystem_models import ShopOrder

    def register(client, phone):
        response = client.post("/api/v1/auth/register", json={
            "phone": phone, "password": "secure-test-password",
        })
        assert response.status_code == 201, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    with TestClient(app) as client:
        suffix = str(uuid.uuid4().int % 100000000).zfill(8)
        buyer_headers = register(client, f"+97674{suffix}")
        seller_headers = register(client, f"+97673{suffix}")
        product = client.post("/api/v1/store/products", headers=seller_headers, json={
            "title": "Төлбөр хүлээгдэж буй бараа", "description": "Pending payment test",
            "category": "training", "price": 25_000, "stock": 2,
        })
        assert product.status_code == 201, product.text
        cart = client.post("/api/v1/store/cart", headers=buyer_headers, json={
            "product_id": product.json()["id"], "quantity": 1,
        })
        assert cart.status_code == 200, cart.text
        order = client.post("/api/v1/store/checkout", headers=buyer_headers, json={
            "delivery_address": "Улаанбаатар хот, pending төлбөрийн тест",
        })
        assert order.status_code == 201, order.text

        monkeypatch.setattr(payment_router, "get_settings", lambda: SimpleNamespace(
            qpay_callback_url="https://api.example.test",
        ))
        invoice_id = "qpay-pending-" + uuid.uuid4().hex
        monkeypatch.setattr(payment_router, "create_invoice", lambda **kwargs: {
            "invoice_id": invoice_id, "qr_text": "qpay-pending-qr",
            "qr_image": "", "qPay_shortUrl": "https://qpay.mn/test", "urls": [],
        })
        invoice = client.post("/api/v1/payments/qpay/invoice", headers=buyer_headers, json={
            "order_type": "store_order", "order_id": order.json()["id"],
        })
        assert invoice.status_code == 201, invoice.text

        monkeypatch.setattr(payment_router, "check_invoice", lambda _invoice_id: {
            "paid_amount": "0.00",
            "rows": [{
                "payment_id": "pending-" + uuid.uuid4().hex,
                "payment_status": "WAITING",
                "payment_amount": "25000.00",
                "payment_currency": "MNT",
            }],
        })
        checked = client.post(
            f"/api/v1/payments/qpay/invoices/{invoice.json()['id']}/check",
            headers=buyer_headers, json={},
        )
        assert checked.status_code == 200, checked.text
        assert checked.json()["status"] == "pending"

        with SessionLocal() as db:
            stored_order = db.get(ShopOrder, order.json()["id"])
            assert stored_order.payment_status == "unpaid"
            assert db.query(PaymentTransaction).filter_by(
                provider="qpay", external_payment_id=invoice_id,
            ).count() == 0

        notifications = client.get("/api/v1/notifications", headers=seller_headers)
        assert notifications.status_code == 200
        assert not any(
            item["category"] == "order" and str(order.json()["id"]) in item["body"]
            for item in notifications.json()
        )

