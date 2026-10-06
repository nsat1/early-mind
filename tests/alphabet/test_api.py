import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.alphabet.content import LETTERS
from app.alphabet.schemas import LetterSummary


@pytest.mark.parametrize(
    ("alphabet_id", "status_code", "expected"),
    [
        (
            "ru",
            200,
            [
                {"id": "a", "symbol": "А", "kind": "vowel"},
                {"id": "m", "symbol": "М", "kind": "consonant"},
                {"id": "o", "symbol": "О", "kind": "vowel"},
                {"id": "u", "symbol": "У", "kind": "vowel"},
            ],
        ),
        ("en", 404, {"detail": "Alphabet not found"}),
    ],
)
def test_list_letters_contract(
    app: FastAPI, alphabet_id: str, status_code: int, expected: object
) -> None:
    with TestClient(app) as client:
        response = client.get(f"/api/v1/alphabets/{alphabet_id}/letters")

    assert response.status_code == status_code
    assert response.headers["content-type"] == "application/json"
    assert response.json() == expected


@pytest.mark.parametrize(
    ("letters", "expected"),
    [
        ([], []),
        (
            [("o", "О", "vowel", 16), ("a", "А", "vowel", 1)],
            [
                {"id": "a", "symbol": "А", "kind": "vowel"},
                {"id": "o", "symbol": "О", "kind": "vowel"},
            ],
        ),
        (
            [
                ("soft", "Ь", "sign", 30),
                ("zh", "Ж", "consonant", 8),
                ("e", "Е", "vowel", 6),
                ("hard", "Ъ", "sign", 28),
                ("m", "М", "consonant", 14),
                ("yo", "Ё", "vowel", 7),
            ],
            [
                {"id": "e", "symbol": "Е", "kind": "vowel"},
                {"id": "yo", "symbol": "Ё", "kind": "vowel"},
                {"id": "zh", "symbol": "Ж", "kind": "consonant"},
                {"id": "m", "symbol": "М", "kind": "consonant"},
                {"id": "hard", "symbol": "Ъ", "kind": "sign"},
                {"id": "soft", "symbol": "Ь", "kind": "sign"},
            ],
        ),
    ],
)
def test_list_letters_orders_by_position(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    letters: list[tuple[str, str, str, int]],
    expected: list[dict[str, str]],
) -> None:
    content = {
        letter_id: {
            "id": letter_id,
            "symbol": symbol,
            "kind": kind,
            "position": position,
        }
        for letter_id, symbol, kind, position in letters
    }
    monkeypatch.setitem(LETTERS, "ru", content)
    with TestClient(app) as client:
        response = client.get("/api/v1/alphabets/ru/letters")

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    ("letter_id", "symbol", "kind", "words"),
    [
        ("a", "А", "vowel", ["арбуз", "автобус", "ананас"]),
        ("m", "М", "consonant", ["мяч", "машина", "медведь"]),
        ("o", "О", "vowel", ["облако", "ослик", "обруч"]),
        ("u", "У", "vowel", ["утка", "улитка", "утюг"]),
    ],
)
def test_get_russian_letter_returns_content(
    app: FastAPI, letter_id: str, symbol: str, kind: str, words: list[str]
) -> None:
    with TestClient(app) as client:
        response = client.get(f"/api/v1/alphabets/ru/letters/{letter_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "id": letter_id,
        "symbol": symbol,
        "kind": kind,
        "words": words,
    }


@pytest.mark.parametrize(
    "alphabet_id,letter_id", [("en", "a"), ("ru", "z"), ("ru", "а"), ("ru", "м")]
)
def test_unknown_alphabet_or_letter_returns_not_found(
    app: FastAPI, alphabet_id: str, letter_id: str
) -> None:
    with TestClient(app) as client:
        response = client.get(f"/api/v1/alphabets/{alphabet_id}/letters/{letter_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Alphabet or letter not found"}


@pytest.mark.parametrize("kind_fields", [{}, {"kind": "unknown"}])
def test_missing_or_unknown_kind_is_rejected(kind_fields: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        LetterSummary.model_validate({"id": "a", "symbol": "А", **kind_fields})


def test_russian_letter_positions_match_alphabet() -> None:
    assert {letter["id"]: letter["position"] for letter in LETTERS["ru"].values()} == {
        "a": 1,
        "m": 14,
        "o": 16,
        "u": 21,
    }
