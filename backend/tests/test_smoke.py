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


def _valid_production_settings(**overrides):
    from app.config import Settings

    values = {
        "app_env": "production",
        "database_url": "postgresql://arena:secret@db.example.mn/arena",
        "jwt_secret": "p" * 48,
        "auto_create_tables": False,
        "cors_origins": "https://arena.example.mn,https://admin.example.mn",
        "qpay_base_url": "https://merchant.qpay.mn",
        "qpay_client_id": "merchant-client",
        "qpay_client_secret": "merchant-secret",
        "qpay_invoice_code": "invoice-code",
        "qpay_callback_url": "https://api.example.mn",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_configuration_accepts_secure_postgresql_and_qpay_settings():
    from app.config import validate_settings

    validate_settings(_valid_production_settings())


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"database_url": "sqlite:///./arena360.db"}, "PostgreSQL"),
        ({"jwt_secret": "short"}, "JWT_SECRET"),
        ({"auto_create_tables": True}, "AUTO_CREATE_TABLES"),
        ({"cors_origins": "http://arena.example.mn"}, "HTTPS origins"),
        ({"qpay_base_url": "https://merchant-sandbox.qpay.mn"}, "merchant.qpay.mn"),
        ({"qpay_client_secret": ""}, "QPay client ID"),
        ({"qpay_callback_url": "http://api.example.mn"}, "HTTPS API origin"),
    ],
)
def test_production_configuration_rejects_unsafe_or_incomplete_values(overrides, message):
    from app.config import validate_settings

    with pytest.raises(RuntimeError, match=message):
        validate_settings(_valid_production_settings(**overrides))

