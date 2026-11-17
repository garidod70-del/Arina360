from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_bootstrap_admin_grants_and_verifies_referee(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_bootstrap_key", "test-bootstrap-key")
    with TestClient(app) as client:
        phone = "+97699123991"
        registered = client.post("/api/v1/auth/register", json={
            "phone": phone, "password": "secure-test-password"
        })
        assert registered.status_code == 201

        denied = client.post("/api/v1/admin/bootstrap", json={"phone": phone})
        assert denied.status_code == 403

        bootstrapped = client.post(
            "/api/v1/admin/bootstrap",
            json={"phone": phone},
            headers={"X-Admin-Bootstrap-Key": "test-bootstrap-key"},
        )
        assert bootstrapped.status_code == 200

        token = client.post("/api/v1/auth/login", json={
            "phone": phone, "password": "secure-test-password"
        }).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        granted = client.post("/api/v1/admin/referees/grant", headers=headers, json={
            "phone": phone, "sport": "Жүдо", "rank": "Улсын",
            "region": "Улаанбаатар", "base_fee": 50000,
        })
        assert granted.status_code == 201
        assert granted.json()["verification_status"] == "pending"

        verified = client.post(
            f"/api/v1/admin/referees/{registered.json()['user']['id']}/verify",
            headers=headers,
            json={"approved": True, "note": "Test licence verified"},
        )
        assert verified.status_code == 200
        assert verified.json()["verification_status"] == "verified"

        duplicate_bootstrap = client.post(
            "/api/v1/admin/bootstrap",
            json={"phone": phone},
            headers={"X-Admin-Bootstrap-Key": "test-bootstrap-key"},
        )
        assert duplicate_bootstrap.status_code == 409
