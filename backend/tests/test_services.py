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
