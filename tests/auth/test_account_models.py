import secrets
from collections.abc import Iterator
from uuid import UUID

import psycopg
import pytest
from psycopg import errors
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Account, Consent
from app.auth.passwords import hash_password

pytestmark = pytest.mark.integration

INSERT_ACCOUNT = (
    "INSERT INTO accounts (email, password_hash) VALUES (%s, 'hash') "
    "RETURNING account_id"
)
INSERT_CONSENT = "INSERT INTO consents (account_id, policy_version) VALUES (%s, %s)"


@pytest.fixture
def account(app_connection: psycopg.Connection) -> Iterator[UUID]:
    with app_connection.transaction(force_rollback=True):
        row = app_connection.execute(INSERT_ACCOUNT, ("anna@example.ru",)).fetchone()
        assert row is not None
        app_connection.execute(INSERT_CONSENT, (row[0], "2026-10-15"))
        yield row[0]


@pytest.mark.parametrize(
    ("email", "constraint"),
    [
        pytest.param("Anna@Example.ru", "ck_accounts_email_lowercase", id="uppercase"),
        pytest.param("anna@example.ru", "uq_accounts_email", id="duplicate"),
    ],
)
def test_database_rejects_invalid_email(
    app_connection: psycopg.Connection, account: UUID, email: str, constraint: str
) -> None:
    with pytest.raises(errors.IntegrityError) as raised:
        app_connection.execute(INSERT_ACCOUNT, (email,))
    assert raised.value.diag.constraint_name == constraint


@pytest.mark.parametrize(
    ("unknown_account", "constraint"),
    [
        pytest.param(False, "pk_consents", id="same-version"),
        pytest.param(True, "fk_consents_account_id_accounts", id="unknown-account"),
    ],
)
def test_database_rejects_invalid_consent(
    app_connection: psycopg.Connection,
    account: UUID,
    unknown_account: bool,
    constraint: str,
) -> None:
    account_id = UUID(int=0) if unknown_account else account
    with pytest.raises(errors.IntegrityError) as raised:
        app_connection.execute(INSERT_CONSENT, (account_id, "2026-10-15"))
    assert raised.value.diag.constraint_name == constraint


def test_new_policy_version_adds_consent(
    app_connection: psycopg.Connection, account: UUID
) -> None:
    app_connection.execute(INSERT_CONSENT, (account, "2027-01-01"))
    versions = app_connection.execute(
        "SELECT policy_version FROM consents ORDER BY policy_version"
    ).fetchall()
    assert versions == [("2026-10-15",), ("2027-01-01",)]


def test_deleting_account_deletes_consents(
    app_connection: psycopg.Connection, account: UUID
) -> None:
    app_connection.execute("DELETE FROM accounts WHERE account_id = %s", (account,))
    assert app_connection.execute("SELECT count(*) FROM consents").fetchone() == (0,)


def test_database_rejects_too_long_email(
    app_connection: psycopg.Connection, account: UUID
) -> None:
    with pytest.raises(errors.StringDataRightTruncation):
        app_connection.execute(INSERT_ACCOUNT, ("a" * 244 + "@example.ru",))


@pytest.mark.anyio
async def test_account_defaults(db_session: AsyncSession) -> None:
    password_hash = hash_password(secrets.token_urlsafe())
    account = Account(email="anna@example.ru", password_hash=password_hash)
    db_session.add(account)
    await db_session.flush()
    consent = Consent(account_id=account.account_id, policy_version="2026-10-15")
    db_session.add(consent)
    await db_session.flush()
    await db_session.refresh(account)
    await db_session.refresh(consent)

    assert account.account_id.version == 7
    assert account.email_verified_at is None
    assert account.created_at.tzinfo is not None
    assert consent.accepted_at >= account.created_at
