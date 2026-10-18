import secrets
import time

import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from redis import Redis as SyncRedis

from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/account"
DAY_SECONDS = 24 * 60 * 60


@pytest.fixture
def session_key(
    client: TestClient,
    stored: psycopg.Connection,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> str:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    login = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PHRASE})
    assert login.status_code == 204
    [key] = redis_store.keys("session:*")
    return key


def assert_rejected(response: Response) -> None:
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith('__Host-session=""; expires=')
    assert "; Max-Age=0; Path=/; SameSite=lax; Secure" in cookie


def test_account_returns_email_and_renews_session(
    client: TestClient, session_key: str, redis_store: SyncRedis
) -> None:
    redis_store.expire(session_key, 100)

    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"email": EMAIL}
    assert 30 * DAY_SECONDS - 60 < redis_store.ttl(session_key) <= 30 * DAY_SECONDS


def test_renewal_stops_at_ninety_days_after_login(
    client: TestClient, session_key: str, redis_store: SyncRedis
) -> None:
    redis_store.hset(session_key, "created_at", int(time.time() - 89.5 * DAY_SECONDS))

    response = client.get(URL)

    assert response.status_code == 200
    half_day = DAY_SECONDS // 2
    assert half_day - 60 < redis_store.ttl(session_key) <= half_day


def test_session_older_than_ninety_days_is_ended(
    client: TestClient, session_key: str, redis_store: SyncRedis
) -> None:
    redis_store.hset(session_key, "created_at", int(time.time() - 90 * DAY_SECONDS))

    assert_rejected(client.get(URL))
    assert not redis_store.exists(session_key)


def test_session_of_deleted_account_is_rejected(
    client: TestClient, session_key: str, stored: psycopg.Connection
) -> None:
    stored.execute("DELETE FROM accounts")

    assert_rejected(client.get(URL))


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-cookie"),
        pytest.param(
            {"Cookie": f"__Host-session={secrets.token_urlsafe(32)}"}, id="unknown"
        ),
    ],
)
def test_request_without_valid_session_is_rejected(
    client: TestClient, headers: dict[str, str]
) -> None:
    assert_rejected(client.get(URL, headers=headers))
