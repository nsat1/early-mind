import asyncio
import os
import secrets
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import Field, SecretStr, ValidationError

from app.core.config import (
    DatabaseSettings,
    MigrationSettings,
    NonEmptyString,
    Settings,
)
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = "early_mind_test"
BACKEND_OPTIONS: dict[str, object] = {"loop_factory": asyncio.SelectorEventLoop}


class AdminSettings(DatabaseSettings):
    postgres_user: NonEmptyString = "early_mind_admin"
    postgres_password: SecretStr = Field(min_length=1)


def database_unavailable(reason: str) -> NoReturn:
    if os.environ.get("CI"):
        pytest.fail(reason, pytrace=False)
    pytest.skip(reason)


def connect(
    settings: DatabaseSettings,
    user: str,
    password: SecretStr,
    dbname: str = TEST_DATABASE,
) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=dbname,
        user=user,
        password=password.get_secret_value(),
        autocommit=True,
        connect_timeout=2,
    )


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


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, backend_options=BACKEND_OPTIONS) as client:
        yield client


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, object]]:
    return "asyncio", BACKEND_OPTIONS


def migrations_config() -> Config:
    return Config(toml_file=str(ROOT / "pyproject.toml"))


@pytest.fixture(scope="session")
def test_database() -> Iterator[None]:
    try:
        admin = AdminSettings()
    except ValidationError:
        database_unavailable("POSTGRES_PASSWORD is not set")

    def as_admin(dbname: str) -> psycopg.Connection:
        return connect(admin, admin.postgres_user, admin.postgres_password, dbname)

    try:
        maintenance = as_admin("postgres")
    except psycopg.OperationalError as error:
        database_unavailable(f"PostgreSQL is unavailable: {error}")
    with maintenance:
        maintenance.execute(f"DROP DATABASE IF EXISTS {TEST_DATABASE} WITH (FORCE)")
        maintenance.execute(f"CREATE DATABASE {TEST_DATABASE}")
    with as_admin(TEST_DATABASE) as database:
        database.execute((ROOT / "scripts/db/grant_privileges.sql").read_bytes())
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DB_NAME", TEST_DATABASE)
        command.upgrade(migrations_config(), "head")
        yield
    with as_admin("postgres") as maintenance:
        maintenance.execute(f"DROP DATABASE {TEST_DATABASE} WITH (FORCE)")


@pytest.fixture
def alembic_config(test_database: None) -> Config:
    return migrations_config()


@pytest.fixture
def migrator_connection(test_database: None) -> Iterator[psycopg.Connection]:
    settings = MigrationSettings()
    with connect(
        settings, settings.db_migration_user, settings.db_migration_password
    ) as connection:
        yield connection


@pytest.fixture
def app_connection(test_database: None) -> Iterator[psycopg.Connection]:
    settings = Settings()
    with connect(settings, settings.db_user, settings.db_password) as connection:
        yield connection
