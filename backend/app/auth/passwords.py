import unicodedata
from functools import cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64
COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")
SERVICE_NAMES = ("earlymind", "early mind", "early-mind", "early_mind")

_password_hasher = PasswordHasher(
    memory_cost=19456, time_cost=2, parallelism=1, salt_len=16, hash_len=32
)


def normalize_password(password: str) -> str:
    return unicodedata.normalize("NFKC", password)


@cache
def common_passwords() -> frozenset[str]:
    return frozenset(COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines())


def check_password(password: str, email: str) -> None:
    normalized = normalize_password(password)
    if not MIN_PASSWORD_LENGTH <= len(normalized) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be {MIN_PASSWORD_LENGTH} to "
            f"{MAX_PASSWORD_LENGTH} characters long"
        )
    lowered = normalized.casefold()
    if lowered in common_passwords() or any(name in lowered for name in SERVICE_NAMES):
        raise ValueError("Password is too common")
    address = email.casefold()
    if lowered in {address, address.partition("@")[0]}:
        raise ValueError("Password must not match email")


def hash_password(password: str) -> str:
    return _password_hasher.hash(normalize_password(password))


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, normalize_password(password))
    except VerifyMismatchError:
        return False
