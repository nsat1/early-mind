import psycopg
import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from redis import Redis as SyncRedis

from app.core.mail import Mail
from tests.auth.accounts import EMAIL, PHRASE, REGISTER_URL, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/account/deletion"
WRONG_PHRASE = "неверная фраза 1"


@pytest.fixture
def device(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> dict[str, str]:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    stored.execute("UPDATE accounts SET email_verified_at = now()")
    return log_in(client)


def log_in(client: TestClient, phrase: str = PHRASE) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": phrase}
    )
    client.cookies.clear()
    session = response.cookies.get("__Host-session")
    return {"Cookie": f"__Host-session={session}"}


def delete(
    client: TestClient, device: dict[str, str], phrase: str = PHRASE
) -> Response:
    return client.post(URL, headers=device, json={"password": phrase})


def test_deletion_leaves_nothing_behind(
    client: TestClient,
    device: dict[str, str],
    stored: psycopg.Connection,
    redis_store: SyncRedis,
) -> None:
    other = log_in(client)
    reset = client.post("/api/v1/auth/password-reset", json={"email": EMAIL})
    assert reset.status_code == 202
    log_in(client, WRONG_PHRASE)
    assert delete(client, device, WRONG_PHRASE).status_code == 403

    response = delete(client, device)

    assert response.status_code == 204
    assert "; Max-Age=0; Path=/; SameSite=lax; Secure" in response.headers["set-cookie"]
    assert stored.execute("SELECT count(*) FROM accounts").fetchone() == (0,)
    assert stored.execute("SELECT count(*) FROM consents").fetchone() == (0,)
    assert set(redis_store.keys("*")) == set(redis_store.keys("rate:*"))
    assert client.get("/api/v1/account", headers=other).status_code == 401


def test_wrong_password_keeps_account(
    client: TestClient, device: dict[str, str]
) -> None:
    response = delete(client, device, WRONG_PHRASE)

    assert response.status_code == 403
    assert response.json()["detail"] == "Incorrect password"
    assert client.get("/api/v1/account", headers=device).status_code == 200


def test_password_attempts_are_shared_with_password_change(
    client: TestClient, device: dict[str, str]
) -> None:
    for _ in range(3):
        change = client.put(
            "/api/v1/account/password",
            headers=device,
            json={"current_password": WRONG_PHRASE, "password": "третья фраза 33"},
        )
        assert change.status_code == 403
    for _ in range(2):
        assert delete(client, device, WRONG_PHRASE).status_code == 403

    assert delete(client, device).status_code == 429


def test_deletion_requires_session(client: TestClient) -> None:
    assert client.post(URL, json={"password": PHRASE}).status_code == 401
