import re

import psycopg
import pytest
from fastapi.testclient import TestClient
from redis import Redis as SyncRedis

from app.auth.tokens import token_hash
from app.core.mail import Mail
from tests.auth.accounts import EMAIL, REGISTER_URL, link_token, registration

pytestmark = pytest.mark.integration

URL = "/api/v1/auth/password-reset"
HOUR_SECONDS = 60 * 60
RESET_SUBJECT = "Восстановление пароля Early Mind"


@pytest.fixture
def account_id(
    client: TestClient, stored: psycopg.Connection, sent_mails: list[Mail]
) -> str:
    assert client.post(REGISTER_URL, json=registration()).status_code == 202
    [(account_id,)] = stored.execute("SELECT account_id FROM accounts")
    return str(account_id)


def reset_key(mail: Mail) -> str:
    return f"reset-token:{token_hash(link_token(mail))}"


def test_reset_link_is_sent_even_before_email_verification(
    client: TestClient,
    account_id: str,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    response = client.post(URL, json={"email": "Anna.Petrova@Mail.ru"})

    assert response.status_code == 202
    assert response.content == b""
    verification, mail = sent_mails
    assert (mail.to, mail.subject) == (EMAIL, RESET_SUBJECT)
    link = re.search(r"https://early-mind\.example/reset-password#token=\S+", mail.body)
    assert link is not None
    key = reset_key(mail)
    assert redis_store.get(key) == account_id
    assert HOUR_SECONDS - 60 < redis_store.ttl(key) <= HOUR_SECONDS
    verification_key = f"email-token:{token_hash(link_token(verification))}"
    assert redis_store.get(verification_key) == account_id


def test_unknown_email_gets_same_response(
    client: TestClient, account_id: str, sent_mails: list[Mail]
) -> None:
    known = client.post(URL, json={"email": EMAIL})
    unknown = client.post(URL, json={"email": "boris.ivanov@mail.ru"})

    assert known.status_code == unknown.status_code == 202
    assert known.headers == unknown.headers
    assert known.content == unknown.content
    assert len(sent_mails) == 2


def test_new_reset_link_replaces_previous(
    client: TestClient,
    account_id: str,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    for _ in range(2):
        assert client.post(URL, json={"email": EMAIL}).status_code == 202

    _, _, latest = sent_mails
    assert redis_store.keys("reset-token:*") == [reset_key(latest)]


def test_reset_mails_share_account_limit(
    client: TestClient,
    account_id: str,
    redis_store: SyncRedis,
    sent_mails: list[Mail],
) -> None:
    for _ in range(3):
        assert client.post(URL, json={"email": EMAIL}).status_code == 202

    subjects = [mail.subject for mail in sent_mails]
    assert subjects == [
        "Подтвердите email для Early Mind",
        RESET_SUBJECT,
        RESET_SUBJECT,
    ]
    assert redis_store.keys("reset-token:*") == [reset_key(sent_mails[-1])]
