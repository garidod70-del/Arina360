from functools import lru_cache
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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env.lower() == "production":
        if settings.jwt_secret == "development-only-change-me" or len(settings.jwt_secret) < 32:
            raise RuntimeError("Production requires a unique JWT_SECRET of at least 32 characters.")
        if settings.auto_create_tables:
            raise RuntimeError("Disable AUTO_CREATE_TABLES in production; use database migrations.")
    return settings
