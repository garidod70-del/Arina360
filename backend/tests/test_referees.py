from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import User, UserRole
from app.referee_models import RefereeProfile


def register(client, phone):
    response = client.post("/api/v1/auth/register", json={"phone": phone, "password": "referee-test-pass"})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_referee_request_assignment_acceptance_completion_and_rating():
    with TestClient(app) as client:
        organizer_token = register(client, "+97699123001")
        referee_token = register(client, "+97699123002")
        organizer_headers = {"Authorization": f"Bearer {organizer_token}"}
        referee_headers = {"Authorization": f"Bearer {referee_token}"}

        # Public registration cannot grant a privileged referee role.
        denied = client.post("/api/v1/referees/profile/me", json={
            "sport": "Жүдо", "rank": "Улсын", "region": "Улаанбаатар", "base_fee": 50000
        }, headers=referee_headers)
        assert denied.status_code == 403

        # Simulate an administrator-approved referee account for integration coverage.
        with SessionLocal() as db:
            referee = db.query(User).filter(User.phone == "+97699123002").one()
            db.add(UserRole(user_id=referee.id, role="referee"))
            db.add(RefereeProfile(
                user_id=referee.id, sport="Жүдо", rank="Улсын",
                region="Улаанбаатар", base_fee=50000,
                verification_status="verified",
            ))
            db.commit()
            referee_id = referee.id

        payload = {
            "sport": "Жүдо", "rank": "Улсын", "booking_type": "Нэг шүүгч",
            "event_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "venue": "Улаанбаатар спорт ордон", "referee_count": 1,
            "payment_type": "Нэг тоглолтоор", "unit_fee": 50000,
            "work_days": 1, "transport_fee": 5000, "food_fee": 0,
            "contact_name": "Тест зохион байгуулагч", "contact_phone": "99123001",
            "notes": "CI тест",
        }
        created = client.post("/api/v1/referees/requests", json=payload, headers=organizer_headers)
        assert created.status_code == 201
        assert created.json()["total_amount"] == 55000
        booking_id = created.json()["id"]

        directory = client.get("/api/v1/referees?sport=Жүдо")
        assert directory.status_code == 200
        assert any(row["user_id"] == referee_id for row in directory.json())

        assigned = client.post(
            f"/api/v1/referees/requests/{booking_id}/assign?referee_user_id={referee_id}",
            headers=organizer_headers,
        )
        assert assigned.status_code == 200
        assert assigned.json()["status"] == "assigned"

        accepted = client.post(
            f"/api/v1/referees/requests/{booking_id}/accept", headers=referee_headers
        )
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        with SessionLocal() as db:
            from app.referee_models import RefereeBooking
            booking = db.get(RefereeBooking, booking_id)
            booking.payment_status = "paid"  # simulate a verified gateway settlement
            db.commit()

        completed = client.post(
            f"/api/v1/referees/requests/{booking_id}/complete", headers=organizer_headers
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "completed"

        rated = client.post(
            f"/api/v1/referees/requests/{booking_id}/rating",
            json={"score": 5, "comment": "Сайн ажилласан"},
            headers=organizer_headers,
        )
        assert rated.status_code == 201
        assert rated.json()["score"] == 5

        duplicate = client.post(
            f"/api/v1/referees/requests/{booking_id}/rating",
            json={"score": 4}, headers=organizer_headers,
        )
        assert duplicate.status_code == 409
