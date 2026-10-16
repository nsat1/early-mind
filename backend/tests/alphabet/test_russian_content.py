import re

from app.alphabet.models import LetterKind
from app.alphabet.source import (
    ALPHABET_FILE,
    CONTENT_DIR,
    LetterSource,
    load_alphabet,
    media_problems,
)

ALPHABET = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
VOWELS = "АЕЁИОУЫЭЮЯ"
SIGNS = "ЪЬ"
NOT_INITIAL = "ЪЫЬ"
WORD = re.compile(r"[а-яё]+")

RUSSIAN = load_alphabet(CONTENT_DIR / "ru" / ALPHABET_FILE)


def expected_kind(symbol: str) -> LetterKind:
    if symbol in VOWELS:
        return LetterKind.VOWEL
    if symbol in SIGNS:
        return LetterKind.SIGN
    return LetterKind.CONSONANT


def word_problems(letter: LetterSource) -> list[str]:
    lowercase = letter.symbol.lower()
    texts = [word.text for word in letter.words]
    problems = [
        f"{letter.symbol}: {text}"
        for text in texts
        if not WORD.fullmatch(text)
        or (letter.symbol in NOT_INITIAL and lowercase not in text)
        or (letter.symbol not in NOT_INITIAL and not text.startswith(lowercase))
    ]
    if len(set(texts)) != len(texts) or len(texts) > 3:
        problems.append(f"{letter.symbol}: {texts}")
    return problems


def test_letters_follow_alphabet() -> None:
    assert [(letter.symbol, letter.position) for letter in RUSSIAN.letters] == [
        (symbol, position) for position, symbol in enumerate(ALPHABET, start=1)
    ]


def test_kinds_match_letters() -> None:
    assert {letter.symbol: letter.kind for letter in RUSSIAN.letters} == {
        symbol: expected_kind(symbol) for symbol in ALPHABET
    }


def test_words_illustrate_letters() -> None:
    assert [
        problem for letter in RUSSIAN.letters for problem in word_problems(letter)
    ] == []


def test_media_files_exist_within_limits() -> None:
    assert media_problems(RUSSIAN, CONTENT_DIR / "ru") == []
