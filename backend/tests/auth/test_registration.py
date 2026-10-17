import re
from unittest.mock import AsyncMock, Mock

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.auth.passwords import verify_password
from app.auth.schemas import PRIVACY_POLICY_VERSION
from app.auth.tokens import token_hash
from app.core.mail import Mail
from app.db.dependencies import get_redis

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/register"
PHRASE = "мама мыла раму 7"
EMAIL = "anna.petrova@mail.ru"
DAY_SECONDS = 24 * 60 * 60


def registration(**changes: object) -> dict[str, object]:
    return {
        "email": "Anna.Petrova@Mail.ru",
        "password": PHRASE,
        "policy_version": PRIVACY_POLICY_VERSION,
        "consent": True,
        "adult": True,
    } | changes


def test_registration_creates_unverified_account(
    client: TestClient,
    stored: psycopg.Connection,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    response = client.post(URL, json=registration())

    assert response.status_code == 202
    assert response.content == b""
    [(account_id, email, password_hash, verified_at, policy_version)] = stored.execute(
        "SELECT account_id, email, password_hash, email_verified_at, policy_version "
        "FROM accounts JOIN consents USING (account_id)"
    ).fetchall()
    assert email == EMAIL
    assert verified_at is None
    assert verify_password(PHRASE, password_hash)
    assert policy_version == PRIVACY_POLICY_VERSION
    [mail] = sent_mails
    assert (mail.to, mail.subject) == (EMAIL, "Подтвердите email для Early Mind")
    link = re.search(r"https://early-mind\.example/verify-email#token=(\S+)", mail.body)
    assert link is not None
    token = link[1]
    assert len(token) == 43
    key = f"email-token:{token_hash(token)}"
    assert redis_store.get(key) == str(account_id)
    assert DAY_SECONDS - 60 < redis_store.ttl(key) <= DAY_SECONDS


def test_existing_email_gets_same_response(
    client: TestClient,
    stored: psycopg.Connection,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    other_phrase = "синий-трамвай-42"
    first = client.post(URL, json=registration())
    second = client.post(
        URL,
        json=registration(email="ANNA.PETROVA@mail.ru", password=other_phrase),
    )

    assert second.status_code == first.status_code == 202
    assert second.headers == first.headers
    assert second.content == first.content
    [(password_hash,)] = stored.execute("SELECT password_hash FROM accounts")
    assert verify_password(PHRASE, password_hash)
    assert len(redis_store.keys("email-token:*")) == 1
    _, mail = sent_mails
    assert (mail.to, mail.subject) == (EMAIL, "Аккаунт Early Mind уже есть")
    assert "https://early-mind.example/login\n" in mail.body
    assert "token" not in mail.body


def test_rejected_password_returns_error_code(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> None:
    email_name = "Anna.Petrova"

    response = client.post(URL, json=registration(password=email_name))

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {
            "in": "body",
            "name": "password",
            "code": "password_matches_email",
            "detail": "Password must not match email",
        }
    ]
    assert stored.execute("SELECT count(*) FROM accounts").fetchone() == (0,)
    assert sent_mails == []


@pytest.mark.parametrize(
    ("changes", "name", "code"),
    [
        pytest.param(
            {"email": "anna.petrova@mail"}, "email", "value_error", id="email"
        ),
        pytest.param({"consent": False}, "consent", "literal_error", id="consent"),
        pytest.param({"adult": False}, "adult", "literal_error", id="adult"),
        pytest.param(
            {"policy_version": "2020-01-01"},
            "policy_version",
            "literal_error",
            id="old-policy",
        ),
    ],
)
def test_registration_requires_valid_fields(
    client: TestClient, changes: dict[str, object], name: str, code: str
) -> None:
    response = client.post(URL, json=registration(**changes))

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert [(error["name"], error["code"]) for error in errors] == [(name, code)]


def test_account_is_not_saved_without_email_token(
    app: FastAPI,
    client: TestClient,
    stored: psycopg.Connection,
    sent_mails: list[Mail],
) -> None:
    failing_redis = Mock(set=AsyncMock(side_effect=RedisConnectionError("down")))
    app.dependency_overrides[get_redis] = lambda: failing_redis

    response = client.post(URL, json=registration())

    assert response.status_code == 503
    assert stored.execute("SELECT count(*) FROM accounts").fetchone() == (0,)
    assert sent_mails == []
