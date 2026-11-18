import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import engine


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"



def test_readiness_checks_database_connection(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["database"] == "connected"



def test_sqlite_enforces_foreign_keys_and_waits_for_short_locks():
    if engine.dialect.name != "sqlite":
        pytest.skip("SQLite-specific connection settings")
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
