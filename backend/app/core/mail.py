import logging
import smtplib
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import Settings, SmtpSecurity

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class Mail:
    to: str
    subject: str
    body: str


def build_message(settings: Settings, mail: Mail) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = mail.to
    message["Subject"] = mail.subject
    message.set_content(mail.body)
    return message


@contextmanager
def smtp_connection(settings: Settings) -> Iterator[smtplib.SMTP]:
    host, port = settings.smtp_host, settings.smtp_port
    if settings.smtp_security is SmtpSecurity.TLS:
        connection = smtplib.SMTP_SSL(
            host,
            port,
            timeout=SMTP_TIMEOUT_SECONDS,
            context=ssl.create_default_context(),
        )
    else:
        connection = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS)
    with connection as smtp:
        if settings.smtp_security is SmtpSecurity.STARTTLS:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username and settings.smtp_password:
            smtp.login(
                settings.smtp_username, settings.smtp_password.get_secret_value()
            )
        yield smtp


def send_mail(settings: Settings, mail: Mail) -> None:
    try:
        with smtp_connection(settings) as smtp:
            smtp.send_message(build_message(settings, mail))
    except OSError as error:
        logger.warning("Mail sending failed: %s", type(error).__name__)
