import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_get_russian_letter_returns_content() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/alphabets/ru/letters/a")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "id": "a",
        "symbol": "А",
        "words": ["арбуз", "автобус", "ананас"],
    }


@pytest.mark.parametrize("alphabet_id,letter_id", [("en", "a"), ("ru", "z")])
def test_unknown_alphabet_or_letter_returns_not_found(
    alphabet_id: str, letter_id: str
) -> None:
    with TestClient(create_app()) as client:
        response = client.get(f"/api/v1/alphabets/{alphabet_id}/letters/{letter_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Alphabet or letter not found"}
