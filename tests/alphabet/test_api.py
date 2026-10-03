import pytest
from fastapi.testclient import TestClient

from app.alphabet.content import LETTERS
from app.main import create_app


@pytest.mark.parametrize(
    ("alphabet_id", "status_code", "expected"),
    [
        (
            "ru",
            200,
            [
                {"id": "a", "symbol": "А"},
                {"id": "o", "symbol": "О"},
                {"id": "u", "symbol": "У"},
            ],
        ),
        ("en", 404, {"detail": "Alphabet not found"}),
    ],
)
def test_list_letters_contract(
    alphabet_id: str, status_code: int, expected: object
) -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/alphabets/{alphabet_id}/letters")

    assert response.status_code == status_code
    assert response.headers["content-type"] == "application/json"
    assert response.json() == expected


@pytest.mark.parametrize(
    ("letters", "expected"),
    [
        ({}, []),
        (
            {"o": {"id": "o", "symbol": "О"}, "a": {"id": "a", "symbol": "А"}},
            [{"id": "o", "symbol": "О"}, {"id": "a", "symbol": "А"}],
        ),
    ],
)
def test_list_letters_preserves_content_order(
    monkeypatch: pytest.MonkeyPatch,
    letters: dict[str, dict[str, str]],
    expected: list[dict[str, str]],
) -> None:
    monkeypatch.setitem(LETTERS, "ru", letters)
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/alphabets/ru/letters")

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    ("letter_id", "symbol", "words"),
    [
        ("a", "А", ["арбуз", "автобус", "ананас"]),
        ("o", "О", ["облако", "ослик", "обруч"]),
        ("u", "У", ["утка", "улитка", "утюг"]),
    ],
)
def test_get_russian_letter_returns_content(
    letter_id: str, symbol: str, words: list[str]
) -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/alphabets/ru/letters/{letter_id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "id": letter_id,
        "symbol": symbol,
        "words": words,
    }


@pytest.mark.parametrize(
    "alphabet_id,letter_id", [("en", "a"), ("ru", "z"), ("ru", "а")]
)
def test_unknown_alphabet_or_letter_returns_not_found(
    alphabet_id: str, letter_id: str
) -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/alphabets/{alphabet_id}/letters/{letter_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Alphabet or letter not found"}
