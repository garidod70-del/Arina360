from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TEST_PASSWORD = "test-password-for-ci-only"

def test_register_login_and_authenticated_profile():
    phone = "+97699123456"
    payload = {"phone": phone, "password": TEST_PASSWORD}
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    body = registered.json()
    assert body["user"]["phone"] == phone
    assert body["user"]["roles"] == ["athlete"]
    assert "password" not in body["user"]
    token = body["access_token"]
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["phone"] == phone
    logged_in = client.post("/api/v1/auth/login", json=payload)
    assert logged_in.status_code == 200
    assert logged_in.json()["token_type"] == "bearer"

def test_duplicate_registration_is_rejected():
    payload = {"phone": "+97699123457", "password": TEST_PASSWORD}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409

def test_wrong_password_is_rejected():
    phone = "+97699123458"
    client.post("/api/v1/auth/register", json={"phone": phone, "password": TEST_PASSWORD})
    response = client.post("/api/v1/auth/login", json={"phone": phone, "password": "not-the-test-password"})
    assert response.status_code == 401
