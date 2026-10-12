from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.alphabet.source import (
    CONTENT_DIR,
    IMAGE_MAX_BYTES,
    SOUND_MAX_BYTES,
    AlphabetSource,
    load_alphabet,
    media_problems,
)

LETTER: dict[str, Any] = {
    "code": "a",
    "symbol": "А",
    "kind": "vowel",
    "position": 1,
    "words": [{"text": "арбуз"}],
}
OTHER: dict[str, Any] = {
    "code": "b",
    "symbol": "Б",
    "kind": "consonant",
    "position": 2,
    "words": [{"text": "банан"}],
}
SIGN: dict[str, Any] = {
    "code": "hard",
    "symbol": "Ъ",
    "kind": "sign",
    "position": 28,
    "words": [{"text": "подъезд"}],
    "explanation": {"pair": ["сел", "съел"]},
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
        pytest.param(
            {"words": [{"text": ""}]}, "string_too_short", "words", id="empty-word"
        ),
        pytest.param({"code": "a" * 21}, "string_too_long", "code", id="long-code"),
        pytest.param(
            {"words": [{"text": "а" * 51}]}, "string_too_long", "words", id="long-word"
        ),
        pytest.param({"words": ["арбуз"]}, "model_type", "words", id="word-as-string"),
        pytest.param(
            {"words": [{"text": "арбуз", "image": "words/arbuz.png"}]},
            "string_pattern_mismatch",
            "words",
            id="unsupported-image",
        ),
        pytest.param(
            {"sound": "letters/a.wav"},
            "string_pattern_mismatch",
            "sound",
            id="unsupported-sound",
        ),
        pytest.param(
            {"sound": "../secrets.mp3"},
            "string_pattern_mismatch",
            "sound",
            id="path-outside-media",
        ),
        pytest.param(
            {"explanation": {"pair": ["сел", "съел", "ел"]}},
            "too_long",
            "explanation",
            id="explanation-not-pair",
        ),
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


@pytest.mark.parametrize(
    "letter",
    [
        pytest.param(SIGN | {"explanation": None}, id="sign-without-explanation"),
        pytest.param(
            LETTER | {"explanation": SIGN["explanation"]}, id="vowel-with-explanation"
        ),
    ],
)
def test_explanation_belongs_to_signs_only(letter: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="required for signs and only for signs"):
        AlphabetSource.model_validate({"id": "ru", "letters": [letter]})


@pytest.mark.parametrize("field", ["code", "position"])
def test_duplicate_letters_are_rejected(field: str) -> None:
    duplicate = OTHER | {field: LETTER[field]}

    with pytest.raises(ValidationError, match=f"Duplicate letter {field}"):
        AlphabetSource.model_validate({"id": "ru", "letters": [LETTER, duplicate]})


@pytest.mark.parametrize(
    ("alphabet", "error_type", "field"),
    [
        pytest.param(
            {"id": "a" * 11, "letters": [LETTER]}, "string_too_long", "id", id="long-id"
        ),
        pytest.param(
            {"id": "ru", "letters": []}, "too_short", "letters", id="no-letters"
        ),
    ],
)
def test_invalid_alphabet_is_rejected(
    alphabet: dict[str, object], error_type: str, field: str
) -> None:
    with pytest.raises(ValidationError) as raised:
        AlphabetSource.model_validate(alphabet)

    [error] = raised.value.errors()
    assert error["type"] == error_type
    assert error["loc"] == (field,)


def test_media_problems_are_reported(tmp_path: Path) -> None:
    media = tmp_path / "ru"
    (media / "letters").mkdir(parents=True)
    (media / "words").mkdir()
    (media / "letters" / "a.mp3").write_bytes(bytes(SOUND_MAX_BYTES))
    (media / "words" / "arbuz.webp").write_bytes(bytes(IMAGE_MAX_BYTES + 1))
    alphabet = AlphabetSource.model_validate(
        {
            "id": "ru",
            "letters": [
                LETTER
                | {
                    "sound": "letters/a.mp3",
                    "words": [
                        {
                            "text": "арбуз",
                            "image": "words/arbuz.webp",
                            "sound": "words/arbuz.mp3",
                        }
                    ],
                },
                SIGN
                | {
                    "explanation": {
                        "pair": ["сел", "съел"],
                        "sound": "letters/hard-explanation.mp3",
                    }
                },
            ],
        }
    )

    assert media_problems(alphabet, tmp_path) == [
        "words/arbuz.mp3: file not found",
        f"words/arbuz.webp: larger than {IMAGE_MAX_BYTES} bytes",
        "letters/hard-explanation.mp3: file not found",
    ]
