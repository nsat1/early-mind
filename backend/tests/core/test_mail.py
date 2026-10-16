import logging
import secrets
import smtplib
from typing import Any

import pytest
from httpx2 import Client
from pydantic import SecretStr

from app.core.config import Settings, SmtpSecurity
from app.core.mail import Mail, build_message, send_mail

MAIL = Mail(to="anna@example.ru", subject="Проверка почты", body="Привет из Early Mind")


class FakeSmtp:
    calls: list[object]

    def __init__(self, host: str, port: int, **options: Any) -> None:
        self.calls = [(type(self).__name__, host, port)]
        connections.append(self)

    def __enter__(self) -> FakeSmtp:
        return self

    def __exit__(self, *error: object) -> None:
        self.calls.append("quit")

    def starttls(self, **options: Any) -> None:
        self.calls.append("starttls")

    def login(self, username: str, password: str) -> None:
        self.calls.append(("login", username, password))

    def send_message(self, message: Any) -> None:
        self.calls.append(("send", message["To"]))


class PlainSmtp(FakeSmtp):
    pass


class TlsSmtp(FakeSmtp):
    pass


connections: list[FakeSmtp] = []


def test_message_supports_cyrillic(settings: Settings) -> None:
    message = build_message(settings, MAIL)

    assert message["From"] == settings.mail_from
    assert message["To"] == MAIL.to
    assert message["Subject"] == MAIL.subject
    assert message.get_content().strip() == MAIL.body
    assert b"=?utf-8?" in message.as_bytes()


@pytest.mark.parametrize(
    ("security", "expected"),
    [
        (SmtpSecurity.NONE, [("PlainSmtp", "smtp.test", 587)]),
        (SmtpSecurity.STARTTLS, [("PlainSmtp", "smtp.test", 587), "starttls"]),
        (SmtpSecurity.TLS, [("TlsSmtp", "smtp.test", 587)]),
    ],
)
def test_connection_follows_security_settings(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    security: SmtpSecurity,
    expected: list[object],
) -> None:
    monkeypatch.setattr(smtplib, "SMTP", PlainSmtp)
    monkeypatch.setattr(smtplib, "SMTP_SSL", TlsSmtp)
    connections.clear()
    password = secrets.token_urlsafe(16)
    configured = settings.model_copy(
        update={
            "smtp_host": "smtp.test",
            "smtp_port": 587,
            "smtp_security": security,
            "smtp_username": "mailer",
            "smtp_password": SecretStr(password),
        }
    )

    send_mail(configured, MAIL)

    [connection] = connections
    assert connection.calls == [
        *expected,
        ("login", "mailer", password),
        ("send", MAIL.to),
        "quit",
    ]


def test_failed_sending_is_logged(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def refuse(*args: object, **options: object) -> None:
        raise ConnectionRefusedError

    monkeypatch.setattr(smtplib, "SMTP", refuse)

    with caplog.at_level(logging.WARNING, logger="app.core.mail"):
        send_mail(settings, MAIL)

    assert caplog.messages == ["Mail sending failed: ConnectionRefusedError"]


@pytest.mark.integration
def test_mail_reaches_mailpit(mailpit: Client) -> None:
    send_mail(Settings(), MAIL)

    [message] = mailpit.get("/api/v1/messages").json()["messages"]
    details = mailpit.get(f"/api/v1/message/{message['ID']}").json()
    assert [recipient["Address"] for recipient in message["To"]] == [MAIL.to]
    assert message["Subject"] == MAIL.subject
    assert details["Text"].strip() == MAIL.body
