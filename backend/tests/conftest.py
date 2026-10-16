import asyncio
import os
import secrets
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import NoReturn

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient, Client, HTTPError
from pydantic import Field, SecretStr, ValidationError
from redis import Redis as SyncRedis
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    DatabaseSettings,
    MigrationSettings,
    NonEmptyString,
    Settings,
)
from app.db.dependencies import get_db_session
from app.db.redis import create_redis
from app.db.session import create_database
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE = "early_mind_test"
TEST_REDIS_DB = 15
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://127.0.0.1:8025")
BACKEND_OPTIONS: dict[str, object] = {"loop_factory": asyncio.SelectorEventLoop}


class AdminSettings(DatabaseSettings):
    postgres_user: NonEmptyString = "early_mind_admin"
    postgres_password: SecretStr = Field(min_length=1)


def service_unavailable(reason: str) -> NoReturn:
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
        redis_host="redis.invalid",
        redis_password=secrets.token_urlsafe(16),
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
        service_unavailable("POSTGRES_PASSWORD is not set")

    def as_admin(dbname: str) -> psycopg.Connection:
        return connect(admin, admin.postgres_user, admin.postgres_password, dbname)

    try:
        maintenance = as_admin("postgres")
    except psycopg.OperationalError as error:
        service_unavailable(f"PostgreSQL is unavailable: {error}")
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
def test_redis() -> Iterator[Settings]:
    try:
        settings = Settings(redis_db=TEST_REDIS_DB)
    except ValidationError:
        service_unavailable("REDIS_PASSWORD is not set")
    with SyncRedis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value(),
        socket_connect_timeout=2,
    ) as client:
        try:
            client.flushdb()
        except RedisError as error:
            service_unavailable(f"Redis is unavailable: {error}")
        yield settings
        client.flushdb()


@pytest.fixture
async def redis_client(test_redis: Settings) -> AsyncIterator[Redis]:
    client = create_redis(test_redis)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def mailpit() -> Iterator[Client]:
    with Client(base_url=MAILPIT_URL, timeout=2) as client:
        try:
            client.delete("/api/v1/messages")
        except HTTPError as error:
            service_unavailable(f"Mailpit is unavailable: {error}")
        yield client
        client.delete("/api/v1/messages")


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


@pytest.fixture
async def db_session(test_database: None) -> AsyncIterator[AsyncSession]:
    engine, _ = create_database(Settings())
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            async with AsyncSession(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            ) as session:
                yield session
            await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def api_client(
    app: FastAPI, db_session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db_session] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
