from fastapi.testclient import TestClient

from app.main import app


def test_profile_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/profile/me")
        assert response.status_code == 401


def test_profile_can_be_created_read_and_updated():
    with TestClient(app) as client:
        registered = client.post(
            "/api/v1/auth/register",
            json={"phone": "+97699123991", "password": "profile-test-password"},
        )
        assert registered.status_code == 201
        token = registered.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        missing = client.get("/api/v1/profile/me", headers=headers)
        assert missing.status_code == 404

        saved = client.put(
            "/api/v1/profile/me",
            headers=headers,
            json={
                "full_name": "Тест Тамирчин",
                "sport": "Жүдо",
                "region": "Улаанбаатар",
            },
        )
        assert saved.status_code == 200
        assert saved.json()["full_name"] == "Тест Тамирчин"
        assert saved.json()["sport"] == "Жүдо"

        updated = client.put(
            "/api/v1/profile/me",
            headers=headers,
            json={"full_name": "Шинэ Нэр", "sport": "Самбо", "region": "Өмнөговь"},
        )
        assert updated.status_code == 200
        assert updated.json()["full_name"] == "Шинэ Нэр"

        fetched = client.get("/api/v1/profile/me", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["sport"] == "Самбо"
