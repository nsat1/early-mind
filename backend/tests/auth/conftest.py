from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl
from redis import Redis as SyncRedis

from app.core.config import Settings
from app.core.mail import Mail


@pytest.fixture
def settings(test_database: None, test_redis: Settings) -> Settings:
    return test_redis.model_copy(
        update={"app_url": HttpUrl("https://early-mind.example/")}
    )


@pytest.fixture
def client(client: TestClient) -> TestClient:
    client.base_url = "https://testserver"
    client.headers["Origin"] = "https://early-mind.example"
    return client


@pytest.fixture
def stored(app_connection: psycopg.Connection) -> Iterator[psycopg.Connection]:
    yield app_connection
    app_connection.execute("DELETE FROM accounts")


@pytest.fixture
def redis_store(settings: Settings) -> Iterator[SyncRedis]:
    with SyncRedis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value(),
        decode_responses=True,
    ) as client:
        yield client


@pytest.fixture
def sent_mails(monkeypatch: pytest.MonkeyPatch) -> list[Mail]:
    mails: list[Mail] = []
    monkeypatch.setattr(
        "app.auth.router.send_mail", lambda settings, mail: mails.append(mail)
    )
    return mails
