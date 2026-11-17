from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from app.main import app


def register(client, phone):
    response = client.post("/api/v1/auth/register", json={"phone": phone, "password": "referee-test-pass"})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_referee_request_assignment_and_rating_requires_verified_role():
    with TestClient(app) as client:
        organizer_token = register(client, "+97699123001")
        referee_token = register(client, "+97699123002")

        payload = {
            "sport": "Жүдо", "rank": "Улсын", "booking_type": "Нэг шүүгч",
            "event_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "venue": "Улаанбаатар спорт ордон", "referee_count": 1,
            "payment_type": "Нэг тоглолтоор", "unit_fee": 50000,
            "work_days": 1, "transport_fee": 5000, "food_fee": 0,
            "contact_name": "Тест зохион байгуулагч", "contact_phone": "99123001",
            "notes": "CI тест",
        }
        headers = {"Authorization": f"Bearer {organizer_token}"}
        created = client.post("/api/v1/referees/requests", json=payload, headers=headers)
        assert created.status_code == 201
        assert created.json()["total_amount"] == 55000
        booking_id = created.json()["id"]

        # Regular athlete accounts cannot self-promote into referees.
        referee_headers = {"Authorization": f"Bearer {referee_token}"}
        denied = client.post("/api/v1/referees/profile/me", json={
            "sport": "Жүдо", "rank": "Улсын", "region": "Улаанбаатар", "base_fee": 50000
        }, headers=referee_headers)
        assert denied.status_code == 403

        mine = client.get("/api/v1/referees/requests/me", headers=headers)
        assert mine.status_code == 200
        assert mine.json()[0]["status"] == "pending"
