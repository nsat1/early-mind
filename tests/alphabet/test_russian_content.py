import re

import pytest

from app.alphabet.models import LetterKind
from app.alphabet.source import (
    CONTENT_DIR,
    MEDIA_DIR,
    LetterSource,
    load_alphabet,
    media_problems,
)

ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
VOWELS = "АЕЁИОУЫЭЮЯ"
SIGNS = "ЪЬ"
NOT_INITIAL = "ЪЫЬ"
WORD = re.compile(r"[а-яё]+")

RUSSIAN = load_alphabet(CONTENT_DIR / "ru.toml")

letters = pytest.mark.parametrize(
    "letter", RUSSIAN.letters, ids=lambda letter: f"ru-{letter.code}"
)


def test_file_lists_whole_alphabet_in_order() -> None:
    assert "".join(letter.symbol for letter in RUSSIAN.letters) == ALPHABET


@letters
def test_position_matches_alphabet(letter: LetterSource) -> None:
    assert letter.symbol in ALPHABET
    assert letter.position == ALPHABET.index(letter.symbol) + 1


@letters
def test_kind_matches_letter(letter: LetterSource) -> None:
    if letter.symbol in VOWELS:
        expected = LetterKind.VOWEL
    elif letter.symbol in SIGNS:
        expected = LetterKind.SIGN
    else:
        expected = LetterKind.CONSONANT
    assert letter.kind is expected


@letters
def test_words_illustrate_letter(letter: LetterSource) -> None:
    lowercase = letter.symbol.lower()
    texts = [word.text for word in letter.words]
    for text in texts:
        assert WORD.fullmatch(text), text
        if letter.symbol in NOT_INITIAL:
            assert lowercase in text, text
        else:
            assert text.startswith(lowercase), text
    assert len(set(texts)) == len(texts)
    assert len(texts) <= 3


@pytest.mark.parametrize(
    "letter",
    [letter for letter in RUSSIAN.letters if letter.explanation is not None],
    ids=lambda letter: f"ru-{letter.code}",
)
def test_explanation_pair_differs_by_sign(letter: LetterSource) -> None:
    assert letter.explanation is not None
    without_sign, with_sign = letter.explanation.pair
    lowercase = letter.symbol.lower()
    assert WORD.fullmatch(without_sign), without_sign
    assert WORD.fullmatch(with_sign), with_sign
    assert lowercase not in without_sign
    assert lowercase in with_sign
    assert with_sign.replace(lowercase, "") == without_sign


def test_media_files_exist_within_limits() -> None:
    assert media_problems(RUSSIAN, MEDIA_DIR) == []
