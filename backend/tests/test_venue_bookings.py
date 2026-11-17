from datetime import date, timedelta
import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_venue_slot_booking_lifecycle():
    from app.database import SessionLocal
    from app.models import User, UserRole

    suffix = str(uuid.uuid4().int % 1000000).zfill(6)
    provider_phone = "+97688" + suffix + "01"
    customer_phone = "+97688" + suffix + "02"
    admin_phone = "+97688" + suffix + "03"

    with TestClient(app) as client:
        provider = client.post("/api/v1/auth/register", json={"phone": provider_phone, "password": "secure-test-password"})
        customer = client.post("/api/v1/auth/register", json={"phone": customer_phone, "password": "secure-test-password"})
        admin = client.post("/api/v1/auth/register", json={"phone": admin_phone, "password": "secure-test-password"})
        assert provider.status_code == customer.status_code == admin.status_code == 201

        db = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.phone == admin_phone).one()
            db.add(UserRole(user_id=admin_user.id, role="admin"))
            db.commit()
        finally:
            db.close()

        provider_headers = {"Authorization": f"Bearer {provider.json()['access_token']}"}
        customer_headers = {"Authorization": f"Bearer {customer.json()['access_token']}"}
        admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}

        profile = client.post("/api/v1/services/providers/me", headers=provider_headers, json={
            "category": "venue_booking", "display_name": "Тест спорт заал",
            "description": "Жүдо болон биеийн тамирын бэлтгэлийн заал түрээс.",
            "region": "Улаанбаатар", "price_from": 40000,
        })
        assert profile.status_code == 201
        verify = client.post(f"/api/v1/services/providers/{profile.json()['id']}/verify",
            headers=admin_headers, json={"approved": True})
        assert verify.status_code == 200

        slot_date = (date.today() + timedelta(days=2)).isoformat()
        slot = client.post("/api/v1/venues/slots", headers=provider_headers, json={
            "venue_name": "Тест спорт заал", "venue_address": "Улаанбаатар хот, Баянзүрх дүүрэг",
            "sport": "Жүдо", "booking_date": slot_date, "start_time": "10:00:00",
            "end_time": "11:00:00", "price": 40000,
        })
        assert slot.status_code == 201
        available = client.get("/api/v1/venues/slots", params={"booking_date": slot_date, "sport": "Жүдо"})
        assert available.status_code == 200
        assert any(item["id"] == slot.json()["id"] for item in available.json())

        booking = client.post(f"/api/v1/venues/slots/{slot.json()['id']}/book",
            headers=customer_headers, json={"contact_phone": customer_phone, "purpose": "Жүдо бэлтгэл"})
        assert booking.status_code == 201
        assert booking.json()["status"] == "pending"

        confirmed = client.post(f"/api/v1/venues/bookings/{booking.json()['id']}/decision",
            headers=provider_headers, json={"accepted": True})
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        cancelled = client.post(f"/api/v1/venues/bookings/{booking.json()['id']}/cancel",
            headers=customer_headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
