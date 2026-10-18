import secrets

import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from redis import Redis as SyncRedis

from app.auth.tokens import token_hash
from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, registration

pytestmark = pytest.mark.integration

LOGOUT_URL = "/api/v1/auth/logout"
LOGOUT_ALL_URL = "/api/v1/auth/logout-all"
ACCOUNT_URL = "/api/v1/account"
OTHER_EMAIL = "boris.ivanov@mail.ru"


@pytest.fixture
def account_id(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> str:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    [(account_id,)] = stored.execute(
        "UPDATE accounts SET email_verified_at = now() RETURNING account_id"
    )
    return str(account_id)


def log_in(client: TestClient, email: str = EMAIL) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PHRASE}
    )
    assert response.status_code == 204
    return response.cookies["__Host-session"]


def with_session(session_id: str) -> dict[str, str]:
    return {"Cookie": f"__Host-session={session_id}"}


def assert_logged_out(response: Response) -> None:
    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith('__Host-session=""; expires=')
    assert "; Max-Age=0; Path=/; SameSite=lax; Secure" in cookie


def test_logout_ends_current_session(
    client: TestClient, account_id: str, redis_store: SyncRedis
) -> None:
    session_id = log_in(client)

    assert_logged_out(client.post(LOGOUT_URL))

    assert redis_store.keys("session:*") == []
    assert redis_store.smembers(f"account-sessions:{account_id}") == set()
    assert client.get(ACCOUNT_URL, headers=with_session(session_id)).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-cookie"),
        pytest.param(with_session(secrets.token_urlsafe(32)), id="unknown"),
    ],
)
def test_logout_without_session_succeeds(
    client: TestClient, headers: dict[str, str]
) -> None:
    assert_logged_out(client.post(LOGOUT_URL, headers=headers))


def test_logout_all_ends_every_session_of_account(
    client: TestClient,
    account_id: str,
    stored: psycopg.Connection,
    redis_store: SyncRedis,
) -> None:
    first, second = log_in(client), log_in(client)
    assert (
        client.post(REGISTER_URL, json=registration(email=OTHER_EMAIL)).status_code
        == 202
    )
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    other = log_in(client, OTHER_EMAIL)

    response = client.post(LOGOUT_ALL_URL, headers=with_session(second))

    assert_logged_out(response)
    assert client.get(ACCOUNT_URL, headers=with_session(first)).status_code == 401
    assert redis_store.keys("session:*") == [f"session:{token_hash(other)}"]
    assert not redis_store.exists(f"account-sessions:{account_id}")


def test_logout_all_requires_session(client: TestClient) -> None:
    response = client.post(LOGOUT_ALL_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
