from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient

from app.main import app


def _register(client, phone):
    response = client.post("/api/v1/auth/register", json={
        "phone": phone,
        "password": "secure-test-password",
    })
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_single_elimination_tournament_registration_draw_and_results():
    suffix = str(uuid.uuid4().int % 1000000).zfill(6)
    with TestClient(app) as client:
        organizer_headers = _register(client, "+97677" + suffix + "01")
        athlete1_headers = _register(client, "+97677" + suffix + "02")
        athlete2_headers = _register(client, "+97677" + suffix + "03")
        athlete3_headers = _register(client, "+97677" + suffix + "04")

        starts_at = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        created = client.post("/api/v1/competitions", headers=organizer_headers, json={
            "title": "ARENA 360 тест жүдо тэмцээн",
            "sport": "Жүдо",
            "format": "single_elimination",
            "region": "Улаанбаатар",
            "venue": "Төв спортын ордон",
            "starts_at": starts_at,
            "max_participants": 8,
        })
        assert created.status_code == 201
        tournament_id = created.json()["id"]

        for index, headers in enumerate([athlete1_headers, athlete2_headers, athlete3_headers], start=1):
            response = client.post(
                f"/api/v1/competitions/{tournament_id}/register",
                headers=headers,
                json={
                    "full_name": f"Тест тамирчин {index}",
                    "club_name": "ARENA клуб",
                    "contact_phone": "+97666" + suffix + f"{index:02d}",
                    "seed": index if index == 1 else 0,
                },
            )
            assert response.status_code == 201

        public = client.get("/api/v1/competitions", params={"sport": "Жүдо"})
        assert public.status_code == 200
        assert any(item["id"] == tournament_id for item in public.json())

        draw = client.post(f"/api/v1/competitions/{tournament_id}/draw", headers=organizer_headers)
        assert draw.status_code == 201
        first_round = [item for item in draw.json() if item["round_number"] == 1]
        final_round = [item for item in draw.json() if item["round_number"] == 2]
        assert len(first_round) == 2
        assert len(final_round) == 1
        bye = next(item for item in first_round if item["status"] == "completed")
        assert bye["winner_id"] is not None
        scheduled = next(item for item in first_round if item["status"] == "scheduled")

        score = client.post(
            f"/api/v1/competitions/{tournament_id}/matches/{scheduled['id']}/score",
            headers=organizer_headers,
            json={"score1": 2, "score2": 1, "mat_name": "Дэвжээ 1"},
        )
        assert score.status_code == 200
        assert score.json()["status"] == "completed"

        matches = client.get(f"/api/v1/competitions/{tournament_id}/matches")
        final = next(item for item in matches.json() if item["round_number"] == 2)
        assert final["status"] == "scheduled"
        assert final["participant1_id"] is not None
        assert final["participant2_id"] is not None

        final_score = client.post(
            f"/api/v1/competitions/{tournament_id}/matches/{final['id']}/score",
            headers=organizer_headers,
            json={"score1": 3, "score2": 0},
        )
        assert final_score.status_code == 200
        detail = client.get(f"/api/v1/competitions/{tournament_id}")
        assert detail.json()["status"] == "completed"


def test_tournament_permissions_and_draw_validation():
    suffix = str(uuid.uuid4().int % 1000000).zfill(6)
    with TestClient(app) as client:
        owner_headers = _register(client, "+97655" + suffix + "01")
        other_headers = _register(client, "+97655" + suffix + "02")
        starts_at = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        created = client.post("/api/v1/competitions", headers=owner_headers, json={
            "title": "Тест тэмцээн",
            "sport": "Волейбол",
            "format": "round_robin",
            "region": "Дархан",
            "venue": "Спорт заал",
            "starts_at": starts_at,
            "max_participants": 4,
        })
        assert created.status_code == 201
        tournament_id = created.json()["id"]

        forbidden = client.post(f"/api/v1/competitions/{tournament_id}/close-registration", headers=other_headers)
        assert forbidden.status_code == 403

        too_early = client.post(f"/api/v1/competitions/{tournament_id}/draw", headers=owner_headers)
        assert too_early.status_code == 400
