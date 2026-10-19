import secrets

import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from redis import Redis as SyncRedis

from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, link_token, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/password-reset/confirm"
NEW_PHRASE = "синий-трамвай-42"
INVALID_LINK = "Invalid or expired link"


@pytest.fixture
def reset_token(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> str:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    reset = client.post("/api/v1/auth/password-reset", json={"email": EMAIL})
    assert reset.status_code == 202
    return link_token(sent_mails[-1])


def log_in(client: TestClient, phrase: str = PHRASE) -> Response:
    return client.post("/api/v1/auth/login", json={"email": EMAIL, "password": phrase})


def confirm(client: TestClient, token: str, phrase: str = NEW_PHRASE) -> Response:
    return client.post(URL, json={"token": token, "password": phrase})


def test_reset_changes_password_and_verifies_email(
    client: TestClient, reset_token: str, sent_mails: list[Mail]
) -> None:
    response = confirm(client, reset_token)

    assert response.status_code == 204
    assert "; Max-Age=0; Path=/; SameSite=lax; Secure" in response.headers["set-cookie"]
    assert (sent_mails[-1].to, sent_mails[-1].subject) == (
        EMAIL,
        "Пароль Early Mind изменён",
    )
    assert log_in(client).status_code == 401
    assert log_in(client, NEW_PHRASE).status_code == 204
    repeated = confirm(client, reset_token)
    assert repeated.status_code == 400
    assert repeated.json()["detail"] == INVALID_LINK


def test_reset_ends_all_sessions(
    client: TestClient,
    reset_token: str,
    stored: psycopg.Connection,
    redis_store: SyncRedis,
) -> None:
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    devices = [log_in(client).cookies["__Host-session"] for _ in range(2)]
    client.cookies.clear()

    assert confirm(client, reset_token).status_code == 204

    for session_id in devices:
        cookie = {"Cookie": f"__Host-session={session_id}"}
        assert client.get("/api/v1/account", headers=cookie).status_code == 401
    assert redis_store.keys("session:*") == []


def test_reset_lifts_login_pause(
    client: TestClient, reset_token: str, stored: psycopg.Connection
) -> None:
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    for _ in range(5):
        assert log_in(client, "неверная фраза 1").status_code == 401
    assert log_in(client, NEW_PHRASE).status_code == 429

    assert confirm(client, reset_token).status_code == 204

    assert log_in(client, NEW_PHRASE).status_code == 204


def test_rejected_password_keeps_link(client: TestClient, reset_token: str) -> None:
    response = confirm(client, reset_token, EMAIL)

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert [(error["name"], error["code"]) for error in errors] == [
        ("password", "password_matches_email")
    ]
    assert confirm(client, reset_token).status_code == 204


def test_unknown_token_is_rejected(client: TestClient) -> None:
    response = confirm(client, secrets.token_urlsafe(32))

    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_LINK


def test_link_of_deleted_account_is_rejected(
    client: TestClient, reset_token: str, stored: psycopg.Connection
) -> None:
    stored.execute("DELETE FROM accounts")

    response = confirm(client, reset_token)

    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_LINK
