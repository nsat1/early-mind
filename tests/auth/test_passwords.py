import secrets

import pytest
from argon2 import Type, extract_parameters
from argon2.exceptions import InvalidHashError

from app.auth.passwords import hash_password, verify_password


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
