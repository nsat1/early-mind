import re

import pytest

from app.alphabet.models import LetterKind
from app.alphabet.source import CONTENT_DIR, LetterSource, load_alphabet

ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
VOWELS = "АЕЁИОУЫЭЮЯ"
SIGNS = "ЪЬ"
NOT_INITIAL = "ЪЫЬ"
WORD = re.compile(r"[а-яё]+")

letters = pytest.mark.parametrize(
    "letter",
    load_alphabet(CONTENT_DIR / "ru.toml").letters,
    ids=lambda letter: f"ru-{letter.code}",
)


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
    for word in letter.words:
        assert WORD.fullmatch(word), word
        if letter.symbol in NOT_INITIAL:
            assert lowercase in word, word
        else:
            assert word.startswith(lowercase), word
    assert len(set(letter.words)) == len(letter.words)
