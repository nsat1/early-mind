import secrets

import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        db_host="db.invalid",
        db_port=5432,
        db_name="early_mind",
        db_user="early_mind_app",
        db_password=secrets.token_urlsafe(16),
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)
