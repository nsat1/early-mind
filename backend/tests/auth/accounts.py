import re

from app.auth.schemas import PRIVACY_POLICY_VERSION
from app.core.mail import Mail

REGISTER_URL = "/api/v1/auth/register"
VERIFY_URL = "/api/v1/auth/email-verification"
EMAIL = "anna.petrova@mail.ru"
PHRASE = "мама мыла раму 7"


def registration(**changes: object) -> dict[str, object]:
    return {
        "email": "Anna.Petrova@Mail.ru",
        "password": PHRASE,
        "policy_version": PRIVACY_POLICY_VERSION,
        "consent": True,
        "adult": True,
    } | changes


def link_token(mail: Mail) -> str:
    link = re.search(r"#token=(\S+)", mail.body)
    assert link is not None
    return link[1]
