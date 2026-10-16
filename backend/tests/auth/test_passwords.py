import secrets

import pytest
from argon2 import Type, extract_parameters
from argon2.exceptions import InvalidHashError

from app.auth.passwords import (
    MIN_PASSWORD_LENGTH,
    PasswordError,
    check_password,
    common_passwords,
    hash_password,
    verify_password,
)

EMAIL = "Anna.Petrova@mail.ru"


def test_password_hashing() -> None:
    password = f" Пароль 🔐 {secrets.token_urlsafe(16)} "
    first, second = hash_password(password), hash_password(password)
    assert first != second
    assert first.split("$")[4] != second.split("$")[4]
    assert extract_parameters(first).type is Type.ID
    assert verify_password(password, first)
    assert not verify_password(password + "!", first)
    assert not verify_password(password.strip(), first)


def test_invalid_hash_is_not_a_password_mismatch() -> None:
    with pytest.raises(InvalidHashError):
        verify_password(secrets.token_urlsafe(16), "invalid-hash")


def test_lookalike_characters_give_same_password() -> None:
    password_hash = hash_password("ｐａｓｓ１２３４５")

    assert verify_password("pass12345", password_hash)


@pytest.mark.parametrize(
    "password",
    ["ёжик 123", "мама мыла раму 7", "синий-трамвай-42", "a" * 8 + "я" * 56],
)
def test_password_is_accepted(password: str) -> None:
    check_password(password, EMAIL)


@pytest.mark.parametrize(
    ("password", "code"),
    [
        pytest.param("абвгдеж", "password_too_short", id="too-short"),
        pytest.param("я" * 65, "password_too_long", id="too-long"),
        pytest.param("QwertyUIOP", "password_too_common", id="common"),
        pytest.param("Мой EarlyMind 2026", "password_too_common", id="service-name"),
        pytest.param("anna.petrova", "password_matches_email", id="email-name"),
        pytest.param("anna.petrova@MAIL.RU", "password_matches_email", id="email"),
    ],
)
def test_password_is_rejected(password: str, code: str) -> None:
    with pytest.raises(PasswordError) as error:
        check_password(password, EMAIL)

    assert error.value.code == code


def test_common_passwords_list_is_normalized() -> None:
    passwords = common_passwords()

    assert len(passwords) > 2000
    assert all(len(password) >= MIN_PASSWORD_LENGTH for password in passwords)
    assert all(password == password.casefold() for password in passwords)
