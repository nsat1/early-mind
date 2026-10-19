import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from redis import Redis as SyncRedis

from app.auth.tokens import token_hash
from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/account/password"
NEW_PHRASE = "синий-трамвай-42"
WRONG_PHRASE = "неверная фраза 1"
PAUSE_SECONDS = 15 * 60


@pytest.fixture
def devices(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> list[dict[str, str]]:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    sessions = [log_in(client, PHRASE).cookies["__Host-session"] for _ in range(2)]
    client.cookies.clear()
    return [{"Cookie": f"__Host-session={session}"} for session in sessions]


def log_in(client: TestClient, phrase: str) -> Response:
    response = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": phrase}
    )
    client.cookies.clear()
    return response


def change(
    client: TestClient,
    device: dict[str, str],
    current: str = PHRASE,
    new: str = NEW_PHRASE,
) -> Response:
    return client.put(
        URL, headers=device, json={"current_password": current, "password": new}
    )


def test_change_keeps_only_current_session(
    client: TestClient,
    devices: list[dict[str, str]],
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    current, other = devices

    assert change(client, current).status_code == 204

    assert client.get("/api/v1/account", headers=current).status_code == 200
    assert client.get("/api/v1/account", headers=other).status_code == 401
    [sessions_key] = redis_store.keys("account-sessions:*")
    current_session = current["Cookie"].removeprefix("__Host-session=")
    assert redis_store.smembers(sessions_key) == {token_hash(current_session)}
    assert log_in(client, PHRASE).status_code == 401
    assert log_in(client, NEW_PHRASE).status_code == 204
    mail = sent_mails[-1]
    assert (mail.to, mail.subject) == (EMAIL, "Пароль Early Mind изменён")
    assert "https://early-mind.example/login\n" in mail.body
    assert "token" not in mail.body


def test_wrong_current_password_is_rejected(
    client: TestClient, devices: list[dict[str, str]]
) -> None:
    response = change(client, devices[0], current=WRONG_PHRASE)

    assert response.status_code == 403
    assert response.json()["detail"] == "Incorrect password"
    assert log_in(client, PHRASE).status_code == 204


def test_password_attempts_are_paused_after_five_failures(
    client: TestClient, devices: list[dict[str, str]]
) -> None:
    for _ in range(5):
        assert change(client, devices[0], current=WRONG_PHRASE).status_code == 403

    response = change(client, devices[0])

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many password attempts"
    assert PAUSE_SECONDS - 60 < int(response.headers["retry-after"]) <= PAUSE_SECONDS


def test_pause_window_starts_at_first_failure_and_restarts_at_fifth(
    client: TestClient, devices: list[dict[str, str]], redis_store: SyncRedis
) -> None:
    assert change(client, devices[0], current=WRONG_PHRASE).status_code == 403
    [key] = redis_store.keys("password-failures:*")
    assert PAUSE_SECONDS - 60 < redis_store.ttl(key) <= PAUSE_SECONDS
    redis_store.expire(key, 100)
    for _ in range(3):
        assert change(client, devices[0], current=WRONG_PHRASE).status_code == 403
    assert redis_store.ttl(key) <= 100

    assert change(client, devices[0], current=WRONG_PHRASE).status_code == 403

    assert PAUSE_SECONDS - 60 < redis_store.ttl(key) <= PAUSE_SECONDS


def test_correct_password_resets_attempts(
    client: TestClient, devices: list[dict[str, str]]
) -> None:
    for _ in range(4):
        assert change(client, devices[0], current=WRONG_PHRASE).status_code == 403
    assert change(client, devices[0]).status_code == 204

    for _ in range(4):
        assert change(client, devices[0], current=WRONG_PHRASE).status_code == 403

    assert change(client, devices[0], NEW_PHRASE, "третья фраза 33").status_code == 204


def test_rejected_new_password_keeps_old_one(
    client: TestClient, devices: list[dict[str, str]]
) -> None:
    response = change(client, devices[0], new=EMAIL)

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert [(error["name"], error["code"]) for error in errors] == [
        ("password", "password_matches_email")
    ]
    assert log_in(client, PHRASE).status_code == 204


def test_change_requires_session(client: TestClient) -> None:
    response = client.put(
        URL, json={"current_password": PHRASE, "password": NEW_PHRASE}
    )

    assert response.status_code == 401
