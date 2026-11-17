from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./arena360.db"
    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = 60
    auto_create_tables: bool = True
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
