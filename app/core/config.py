from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EARLY_MIND_",
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )
    db_host: NonEmptyString = "127.0.0.1"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: NonEmptyString = "early_mind"
    db_user: NonEmptyString = "early_mind_app"
    db_password: SecretStr = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
