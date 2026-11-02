from functools import lru_cache
from typing import Self

from pydantic import EmailStr, Field, PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    """Typed app config, read from environment variables (and `.env` locally)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"  # development | test | production
    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://krystian:krystian@localhost:5432/krystian")
    )
    redis_url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))
    cors_origins: list[str] = ["http://localhost:4321", "http://localhost:5173"]

    # --- Auth ---
    secret_key: SecretStr = SecretStr(DEV_SECRET)
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    cookie_secure: bool = False  # True in production (HTTPS only)
    cookie_domain: str | None = None
    login_rate_limit: int = 10  # attempts per IP per window
    login_rate_window_seconds: int = 900

    # --- Public API cache ---
    public_cache_ttl_seconds: int = 3600

    # --- Contact form ---
    contact_rate_limit: int = 5  # messages per IP per window
    contact_rate_window_seconds: int = 3600
    turnstile_secret: SecretStr | None = None  # when set, a valid Turnstile token is required

    # --- Email (Mailpit locally, Resend/any SMTP in production) ---
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = False
    mail_from: str = "Krystian Portfolio <noreply@krystian.dev>"
    notify_email: EmailStr | None = None  # where new-lead notifications go; unset = don't send

    # --- Development conveniences (ignored in production) ---
    dev_admin_email: EmailStr | None = None
    dev_admin_password: SecretStr | None = None

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> Self:
        if self.is_production and self.secret_key.get_secret_value() == DEV_SECRET:
            raise ValueError("SECRET_KEY must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
