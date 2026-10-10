from pathlib import Path

import pytest
from pydantic import ValidationError

from app.alphabet.source import CONTENT_DIR, AlphabetSource, load_alphabet

LETTER = {
    "code": "a",
    "symbol": "А",
    "kind": "vowel",
    "position": 1,
    "words": ["арбуз"],
}
OTHER = {
    "code": "b",
    "symbol": "Б",
    "kind": "consonant",
    "position": 2,
    "words": ["банан"],
}


@pytest.mark.parametrize(
    "path", sorted(CONTENT_DIR.glob("*.toml")), ids=lambda path: path.name
)
def test_content_file_is_valid(path: Path) -> None:
    alphabet = load_alphabet(path)

    assert alphabet.id == path.stem
    assert alphabet.letters


@pytest.mark.parametrize(
    ("changes", "error_type", "field"),
    [
        pytest.param({"kind": "letter"}, "enum", "kind", id="unknown-kind"),
        pytest.param({"kidn": "vowel"}, "extra_forbidden", "kidn", id="extra-key"),
        pytest.param({"position": 0}, "greater_than", "position", id="zero-position"),
        pytest.param({"code": "A"}, "string_pattern_mismatch", "code", id="bad-code"),
        pytest.param({"symbol": "АБ"}, "string_too_long", "symbol", id="long-symbol"),
        pytest.param({"words": []}, "too_short", "words", id="no-words"),
        pytest.param({"words": [""]}, "string_too_short", "words", id="empty-word"),
        pytest.param({"code": "a" * 21}, "string_too_long", "code", id="long-code"),
        pytest.param({"words": ["а" * 51]}, "string_too_long", "words", id="long-word"),
    ],
)
def test_invalid_letter_is_rejected(
    changes: dict[str, object], error_type: str, field: str
) -> None:
    with pytest.raises(ValidationError) as raised:
        AlphabetSource.model_validate({"id": "ru", "letters": [LETTER | changes]})

    [error] = raised.value.errors()
    assert error["type"] == error_type
    assert error["loc"][:3] == ("letters", 0, field)


@pytest.mark.parametrize("field", ["code", "position"])
def test_duplicate_letters_are_rejected(field: str) -> None:
    duplicate = OTHER | {field: LETTER[field]}

    with pytest.raises(ValidationError, match=f"Duplicate letter {field}"):
        AlphabetSource.model_validate({"id": "ru", "letters": [LETTER, duplicate]})


def test_long_alphabet_id_is_rejected() -> None:
    with pytest.raises(ValidationError) as raised:
        AlphabetSource.model_validate({"id": "a" * 11, "letters": [LETTER]})

    [error] = raised.value.errors()
    assert error["type"] == "string_too_long"
    assert error["loc"] == ("id",)
