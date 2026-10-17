import time

import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from redis import Redis as SyncRedis

from app.auth.tokens import token_hash
from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/login"
CREDENTIALS = {"email": "Anna.Petrova@Mail.ru", "password": PHRASE}
DAY_SECONDS = 24 * 60 * 60


def session_id(response: Response) -> str:
    name, _, rest = response.headers["set-cookie"].partition("=")
    value, attributes = rest.split("; ", 1)
    assert name == "__Host-session"
    assert attributes == "HttpOnly; Max-Age=7776000; Path=/; SameSite=lax; Secure"
    return value


@pytest.fixture
def registered(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> str:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    [(account_id,)] = stored.execute("SELECT account_id FROM accounts")
    return str(account_id)


@pytest.fixture
def account_id(registered: str, stored: psycopg.Connection) -> str:
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    return registered


def test_login_creates_session(
    client: TestClient, account_id: str, redis_store: SyncRedis
) -> None:
    response = client.post(URL, json=CREDENTIALS)

    assert response.status_code == 204
    session = session_id(response)
    assert len(session) == 43
    key = f"session:{token_hash(session)}"
    assert redis_store.hget(key, "account_id") == account_id
    assert abs(time.time() - int(redis_store.hget(key, "created_at"))) < 60
    assert 30 * DAY_SECONDS - 60 < redis_store.ttl(key) <= 30 * DAY_SECONDS
    sessions = f"account-sessions:{account_id}"
    assert redis_store.smembers(sessions) == {token_hash(session)}
    assert 90 * DAY_SECONDS - 60 < redis_store.ttl(sessions) <= 90 * DAY_SECONDS
    assert not any(session in stored_key for stored_key in redis_store.keys())


def test_each_login_creates_new_session(
    client: TestClient, account_id: str, redis_store: SyncRedis
) -> None:
    first = session_id(client.post(URL, json=CREDENTIALS))
    second = session_id(client.post(URL, json=CREDENTIALS))

    assert first != second
    assert redis_store.smembers(f"account-sessions:{account_id}") == {
        token_hash(first),
        token_hash(second),
    }


def test_wrong_password_and_unknown_email_look_the_same(
    client: TestClient, account_id: str
) -> None:
    other_phrase = "синий-трамвай-42"

    wrong = client.post(URL, json={"email": EMAIL, "password": other_phrase})
    unknown = client.post(URL, json=CREDENTIALS | {"email": "boris.ivanov@mail.ru"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.headers == unknown.headers
    assert wrong.content == unknown.content
    assert wrong.json()["detail"] == "Invalid email or password"
    assert "set-cookie" not in wrong.headers


def test_unverified_email_is_reported_only_after_correct_password(
    client: TestClient, registered: str
) -> None:
    other_phrase = "синий-трамвай-42"

    correct = client.post(URL, json=CREDENTIALS)
    wrong = client.post(URL, json={"email": EMAIL, "password": other_phrase})

    assert correct.status_code == 403
    assert correct.json()["detail"] == "Email not verified"
    assert "set-cookie" not in correct.headers
    assert wrong.status_code == 401
