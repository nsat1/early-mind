import re
import secrets
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis

from app.auth.schemas import PRIVACY_POLICY_VERSION
from app.core.mail import Mail

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/email-verification"
INVALID_LINK = "Invalid or expired link"
VERIFIED_AT = datetime(2026, 1, 15, 9, 30, tzinfo=UTC)


@pytest.fixture
def token(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "anna.petrova@mail.ru",
            "password": "мама мыла раму 7",
            "policy_version": PRIVACY_POLICY_VERSION,
            "consent": True,
            "adult": True,
        },
    )
    assert response.status_code == 202
    [mail] = sent_mails
    link = re.search(r"#token=(\S+)", mail.body)
    assert link is not None
    return link[1]


def test_email_is_verified_only_once(
    client: TestClient,
    token: str,
    stored: psycopg.Connection,
    redis_store: SyncRedis,
) -> None:
    response = client.post(URL, json={"token": token})

    assert response.status_code == 204
    assert response.content == b""
    [(verified_at,)] = stored.execute("SELECT email_verified_at FROM accounts")
    assert datetime.now(UTC) - timedelta(minutes=1) < verified_at
    assert redis_store.keys("email-token:*") == []
    repeated = client.post(URL, json={"token": token})
    assert repeated.status_code == 400
    assert repeated.json()["detail"] == INVALID_LINK


def test_unknown_token_is_rejected(client: TestClient) -> None:
    response = client.post(URL, json={"token": secrets.token_urlsafe(32)})

    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_LINK


def test_link_of_deleted_account_is_rejected(
    client: TestClient, token: str, stored: psycopg.Connection
) -> None:
    stored.execute("DELETE FROM accounts")

    response = client.post(URL, json={"token": token})

    assert response.status_code == 400
    assert response.json()["detail"] == INVALID_LINK


def test_first_verification_time_is_kept(
    client: TestClient, token: str, stored: psycopg.Connection
) -> None:
    stored.execute("UPDATE accounts SET email_verified_at = %s", (VERIFIED_AT,))

    response = client.post(URL, json={"token": token})

    assert response.status_code == 204
    [(verified_at,)] = stored.execute("SELECT email_verified_at FROM accounts")
    assert verified_at == VERIFIED_AT
