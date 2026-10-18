import hashlib
import hmac

import psycopg
import pytest
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis

from app.core.config import Settings
from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/login"
PAUSE_SECONDS = 15 * 60
OTHER_PHRASE = "синий-трамвай-42"


@pytest.fixture
def account(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> None:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    stored.execute("UPDATE accounts SET email_verified_at = now()")


def fail(client: TestClient, email: str, times: int) -> None:
    for _ in range(times):
        response = client.post(URL, json={"email": email, "password": OTHER_PHRASE})
        assert response.status_code == 401


def login(client: TestClient, email: str = EMAIL) -> int:
    return client.post(URL, json={"email": email, "password": PHRASE}).status_code


def test_login_is_paused_after_five_failures(client: TestClient, account: None) -> None:
    fail(client, "Anna.Petrova@Mail.ru", 5)

    response = client.post(URL, json={"email": EMAIL, "password": PHRASE})

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many login attempts"
    assert PAUSE_SECONDS - 60 < int(response.headers["retry-after"]) <= PAUSE_SECONDS


def test_unknown_email_is_paused_the_same_way(client: TestClient) -> None:
    unknown = "boris.ivanov@mail.ru"
    fail(client, unknown, 5)

    assert login(client, unknown) == 429


def test_successful_login_resets_failures(client: TestClient, account: None) -> None:
    fail(client, EMAIL, 4)
    assert login(client) == 204

    fail(client, EMAIL, 4)

    assert login(client) == 204


def test_correct_password_of_unverified_email_resets_failures(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> None:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    fail(client, EMAIL, 4)
    assert login(client) == 403

    fail(client, EMAIL, 4)

    assert login(client) == 403


def test_window_starts_at_first_failure_and_pause_at_fifth(
    client: TestClient, account: None, settings: Settings, redis_store: SyncRedis
) -> None:
    secret = settings.auth_secret.get_secret_value().encode()
    digest = hmac.new(secret, EMAIL.encode(), hashlib.sha256).hexdigest()
    key = f"login-failures:{digest}"

    fail(client, EMAIL, 1)
    assert redis_store.keys("login-failures:*") == [key]
    assert PAUSE_SECONDS - 60 < redis_store.ttl(key) <= PAUSE_SECONDS
    redis_store.expire(key, 100)
    fail(client, EMAIL, 3)
    assert redis_store.ttl(key) <= 100
    fail(client, EMAIL, 1)

    assert PAUSE_SECONDS - 60 < redis_store.ttl(key) <= PAUSE_SECONDS
