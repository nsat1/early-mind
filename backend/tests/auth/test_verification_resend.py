import psycopg
import pytest
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis

from app.core.mail import Mail
from tests.auth.accounts import (
    EMAIL,
    REGISTER_URL,
    VERIFY_URL,
    link_token,
    registration,
)

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/email-verification/resend"
HOUR_SECONDS = 60 * 60


@pytest.fixture
def registered(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> None:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202


def test_new_link_replaces_previous(
    client: TestClient, registered: None, sent_mails: list[Mail]
) -> None:
    response = client.post(URL, json={"email": "Anna.Petrova@Mail.ru"})

    assert response.status_code == 202
    assert response.content == b""
    first, second = sent_mails
    assert (second.to, second.subject) == (EMAIL, "Подтвердите email для Early Mind")
    assert client.post(VERIFY_URL, json={"token": link_token(first)}).status_code == 400
    assert (
        client.post(VERIFY_URL, json={"token": link_token(second)}).status_code == 204
    )


def test_no_mail_for_verified_or_unknown_email(
    client: TestClient,
    registered: None,
    stored: psycopg.Connection,
    sent_mails: list[Mail],
) -> None:
    stored.execute("UPDATE accounts SET email_verified_at = now()")

    verified = client.post(URL, json={"email": EMAIL})
    unknown = client.post(URL, json={"email": "boris.ivanov@mail.ru"})

    assert verified.status_code == unknown.status_code == 202
    assert verified.headers == unknown.headers
    assert verified.content == unknown.content
    assert len(sent_mails) == 1


def test_mails_are_limited_per_account(
    client: TestClient,
    registered: None,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    [counter] = redis_store.keys("emails:*")
    assert HOUR_SECONDS - 60 < redis_store.ttl(counter) <= HOUR_SECONDS
    redis_store.expire(counter, 100)

    for _ in range(3):
        assert client.post(URL, json={"email": EMAIL}).status_code == 202

    assert len(sent_mails) == 3
    assert redis_store.ttl(counter) <= 100
    last = link_token(sent_mails[-1])
    assert client.post(VERIFY_URL, json={"token": last}).status_code == 204
