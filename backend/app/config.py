from functools import lru_cache
from urllib.parse import urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./arena360.db"
    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = 60
    auto_create_tables: bool = True
    cors_origins: str = "http://localhost:3000"
    admin_bootstrap_key: str = ""
    payment_webhook_secret: str = ""
    qpay_base_url: str = "https://merchant-sandbox.qpay.mn"
    qpay_client_id: str = ""
    qpay_client_secret: str = ""
    qpay_invoice_code: str = ""
    qpay_callback_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def validate_settings(settings: Settings) -> None:
    """Fail closed when production settings are incomplete or unsafe."""
    if settings.app_env.lower() != "production":
        return

    if settings.jwt_secret == "development-only-change-me" or len(settings.jwt_secret) < 32:
        raise RuntimeError("Production requires a unique JWT_SECRET of at least 32 characters.")
    if settings.auto_create_tables:
        raise RuntimeError("Disable AUTO_CREATE_TABLES in production; use database migrations.")
    if not settings.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Production requires PostgreSQL; SQLite is for local development only.")

    origins = settings.cors_origin_list
    if not origins or any(
        urlsplit(origin).scheme != "https"
        or not urlsplit(origin).hostname
        or urlsplit(origin).path not in ("", "/")
        or urlsplit(origin).query
        or urlsplit(origin).fragment
        for origin in origins
    ):
        raise RuntimeError("Production CORS_ORIGINS must contain only HTTPS origins.")

    if settings.qpay_base_url.rstrip("/") != "https://merchant.qpay.mn":
        raise RuntimeError("Production QPay must use https://merchant.qpay.mn, not the sandbox.")
    if not settings.qpay_client_id or not settings.qpay_client_secret or not settings.qpay_invoice_code:
        raise RuntimeError("Production QPay client ID, client secret and invoice code are required.")
    callback = urlsplit(settings.qpay_callback_url)
    if callback.scheme != "https" or not callback.hostname:
        raise RuntimeError("Production QPAY_CALLBACK_URL must be a public HTTPS API origin.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    validate_settings(settings)
    return settings
