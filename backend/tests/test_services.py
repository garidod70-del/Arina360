from fastapi.testclient import TestClient

from app.main import app


def test_service_categories_and_public_directory():
    with TestClient(app) as client:
        categories = client.get("/api/v1/services/categories")
        assert categories.status_code == 200
        assert len(categories.json()) == 10
        slugs = {item["slug"] for item in categories.json()}
        assert "coach" in slugs
        assert "sports_doctor" in slugs
        assert "venue_booking" in slugs
        assert "clubs_training" in slugs

        providers = client.get("/api/v1/services/providers", params={"category": "coach"})
        assert providers.status_code == 200
        assert isinstance(providers.json(), list)


def test_service_provider_verification_and_request_lifecycle():
    import uuid

    from app.database import SessionLocal
    from app.models import User, UserRole

    suffix = str(uuid.uuid4().int % 1000000).zfill(6)
    provider_phone = "+97699" + suffix + "01"
    requester_phone = "+97699" + suffix + "02"
    admin_phone = "+97699" + suffix + "03"

    with TestClient(app) as client:
        provider = client.post("/api/v1/auth/register", json={
            "phone": provider_phone, "password": "secure-test-password"
        })
        requester = client.post("/api/v1/auth/register", json={
            "phone": requester_phone, "password": "secure-test-password"
        })
        admin = client.post("/api/v1/auth/register", json={
            "phone": admin_phone, "password": "secure-test-password"
        })
        assert provider.status_code == 201
        assert requester.status_code == 201
        assert admin.status_code == 201

        db = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.phone == admin_phone).one()
            db.add(UserRole(user_id=admin_user.id, role="admin"))
            db.commit()
        finally:
            db.close()

        provider_token = provider.json()["access_token"]
        requester_token = requester.json()["access_token"]
        admin_token = admin.json()["access_token"]
        provider_headers = {"Authorization": f"Bearer {provider_token}"}
        requester_headers = {"Authorization": f"Bearer {requester_token}"}
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        profile = client.post("/api/v1/services/providers/me", headers=provider_headers, json={
            "category": "coach",
            "display_name": "Тест дасгалжуулагч",
            "description": "Тамирчдад зориулсан спортын бэлтгэл.",
            "sport": "Жүдо",
            "region": "Улаанбаатар",
            "price_from": 50000,
            "credentials": "Тестийн сертификат",
        })
        assert profile.status_code == 201
        assert profile.json()["verification_status"] == "pending"
        provider_id = profile.json()["id"]
        provider_user_id = profile.json()["user_id"]

        hidden = client.get("/api/v1/services/providers", params={"category": "coach"})
        assert hidden.status_code == 200
        assert all(item["user_id"] != provider_user_id for item in hidden.json())

        verified = client.post(
            f"/api/v1/services/providers/{provider_id}/verify",
            headers=admin_headers,
            json={"approved": True, "note": "Тестийн баримт шалгасан."},
        )
        assert verified.status_code == 200
        assert verified.json()["verification_status"] == "verified"

        visible = client.get("/api/v1/services/providers", params={"category": "coach"})
        assert visible.status_code == 200
        assert any(item["user_id"] == provider_user_id for item in visible.json())

        request = client.post("/api/v1/services/requests", headers=requester_headers, json={
            "category": "coach",
            "provider_user_id": provider_user_id,
            "title": "Хувийн бэлтгэлийн хүсэлт",
            "details": "Долоо хоногт гурван удаа жүдо бэлтгэл хийх хүсэлтэй.",
            "sport": "Жүдо",
            "region": "Улаанбаатар",
            "contact_phone": requester_phone,
        })
        assert request.status_code == 201
        request_id = request.json()["id"]
        assert request.json()["status"] == "pending"

        accepted = client.post(
            f"/api/v1/services/requests/{request_id}/respond",
            headers=provider_headers,
            json={"accepted": True, "note": "Бэлтгэлийн цаг санал болгоно."},
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        with SessionLocal() as db:
            from app.service_models import ServiceRequest
            service_request = db.get(ServiceRequest, request_id)
            service_request.payment_status = "paid"  # simulate a verified gateway settlement
            db.commit()

        completed = client.post(
            f"/api/v1/services/requests/{request_id}/complete",
            headers=requester_headers,
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"
