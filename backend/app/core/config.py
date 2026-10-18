from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, HttpUrl, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SmtpSecurity(StrEnum):
    NONE = "none"
    STARTTLS = "starttls"
    TLS = "tls"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )
    db_host: NonEmptyString = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: NonEmptyString = "early_mind"


class Settings(DatabaseSettings):
    db_user: NonEmptyString = "early_mind_app"
    db_password: SecretStr = Field(min_length=1)
    redis_host: NonEmptyString = "127.0.0.1"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_password: SecretStr = Field(min_length=1)
    smtp_host: NonEmptyString = "127.0.0.1"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_security: SmtpSecurity = SmtpSecurity.NONE
    smtp_username: NonEmptyString | None = None
    smtp_password: SecretStr | None = None
    mail_from: NonEmptyString = "Early Mind <no-reply@early-mind.local>"
    app_url: HttpUrl = HttpUrl("http://localhost:5173")
    auth_secret: SecretStr = Field(min_length=32)


class MigrationSettings(DatabaseSettings):
    db_migration_user: NonEmptyString = "early_mind_migrator"
    db_migration_password: SecretStr = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
