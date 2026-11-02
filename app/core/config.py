from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed app config, read from environment variables (and `.env` locally)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://krystian:krystian@localhost:5432/krystian")
    )
    redis_url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))
    # Comma-separated list in env, e.g. "http://localhost:4321,http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:4321", "http://localhost:5173"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
