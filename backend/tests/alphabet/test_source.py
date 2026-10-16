from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.alphabet.source import (
    IMAGE_MAX_BYTES,
    SOUND_MAX_BYTES,
    AlphabetSource,
    alphabet_files,
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
}


@pytest.mark.parametrize("path", alphabet_files(), ids=lambda path: path.parent.name)
def test_content_file_is_valid(path: Path) -> None:
    alphabet = load_alphabet(path)

    assert alphabet.id == path.parent.name
    assert alphabet.letters


@pytest.mark.parametrize(
    ("changes", "error_type", "field"),
    [
        pytest.param({"kidn": "vowel"}, "extra_forbidden", "kidn", id="extra-key"),
        pytest.param({"code": "A"}, "string_pattern_mismatch", "code", id="bad-code"),
        pytest.param({"words": []}, "too_short", "words", id="no-words"),
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


def test_media_problems_are_reported(tmp_path: Path) -> None:
    (tmp_path / "letters").mkdir()
    (tmp_path / "words").mkdir()
    (tmp_path / "letters" / "a.mp3").write_bytes(bytes(SOUND_MAX_BYTES))
    (tmp_path / "words" / "arbuz.webp").write_bytes(bytes(IMAGE_MAX_BYTES + 1))
    alphabet = AlphabetSource.model_validate(
        {
            "id": "ru",
            "letters": [
                LETTER
                | {
                    "sound": "letters/a.mp3",
                    "image": "letters/a.webp",
                    "words": [
                        {
                            "text": "арбуз",
                            "image": "words/arbuz.webp",
                            "sound": "words/arbuz.mp3",
                        }
                    ],
                },
                SIGN | {"sound": "letters/hard.mp3"},
            ],
        }
    )

    assert media_problems(alphabet, tmp_path) == [
        "words/arbuz.mp3: file not found",
        "letters/a.webp: file not found",
        f"words/arbuz.webp: larger than {IMAGE_MAX_BYTES} bytes",
        "letters/hard.mp3: file not found",
    ]
