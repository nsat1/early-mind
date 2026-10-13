import hashlib
from pathlib import Path
from typing import Any

import pytest
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.alphabet.source import AlphabetSource
from app.alphabet.sync import sync_alphabet
from app.core.errors import PROBLEM_MEDIA_TYPE

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


def letter(
    code: str, symbol: str, kind: str, position: int, *texts: str
) -> dict[str, Any]:
    return {
        "code": code,
        "symbol": symbol,
        "kind": kind,
        "position": position,
        "words": [{"text": text} for text in texts],
    }


RUSSIAN = AlphabetSource.model_validate(
    {
        "id": "ru",
        "letters": [
            letter("soft", "Ь", "sign", 30, "конь"),
            letter("m", "М", "consonant", 14)
            | {
                "sound": "letters/m.mp3",
                "image": "letters/m.webp",
                "words": [
                    {
                        "text": "мяч",
                        "image": "words/myach.webp",
                        "sound": "words/myach.mp3",
                    },
                    {"text": "машина"},
                ],
            },
            letter("a", "А", "vowel", 1, "арбуз", "автобус", "ананас"),
            letter("yo", "Ё", "vowel", 7, "ёж"),
        ],
    }
)
ENGLISH = AlphabetSource.model_validate(
    {"id": "en", "letters": [letter("a", "A", "vowel", 1, "apple")]}
)


MEDIA = {
    "letters/m.mp3": b"m sound",
    "letters/m.webp": b"m image",
    "words/myach.webp": b"ball image",
    "words/myach.mp3": b"ball sound",
}


def media_url(path: str) -> str:
    version = hashlib.sha256(MEDIA[path]).hexdigest()[:8]
    return f"/media/ru/{path}?v={version}"


@pytest.fixture(autouse=True)
async def alphabets(db_session: AsyncSession, tmp_path: Path) -> None:
    for path, content in MEDIA.items():
        (tmp_path / path).parent.mkdir(exist_ok=True)
        (tmp_path / path).write_bytes(content)
    await sync_alphabet(db_session, RUSSIAN, tmp_path)
    await sync_alphabet(db_session, ENGLISH)


async def test_list_letters_orders_by_position(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/alphabets/ru/letters")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == [
        {"code": "a", "symbol": "А", "kind": "vowel", "image_url": None},
        {"code": "yo", "symbol": "Ё", "kind": "vowel", "image_url": None},
        {
            "code": "m",
            "symbol": "М",
            "kind": "consonant",
            "image_url": media_url("letters/m.webp"),
        },
        {"code": "soft", "symbol": "Ь", "kind": "sign", "image_url": None},
    ]


@pytest.mark.parametrize(
    ("kind", "codes"),
    [("vowel", ["a", "yo"]), ("consonant", ["m"]), ("sign", ["soft"])],
)
async def test_list_letters_filters_by_kind(
    api_client: AsyncClient, kind: str, codes: list[str]
) -> None:
    response = await api_client.get(
        "/api/v1/alphabets/ru/letters", params={"kind": kind}
    )

    assert response.status_code == 200
    assert [letter["code"] for letter in response.json()] == codes


async def test_filter_without_matches_returns_empty_list(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/alphabets/en/letters", params={"kind": "sign"}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_unknown_alphabet_returns_not_found(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/alphabets/de/letters")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json()["detail"] == "Alphabet not found"


@pytest.mark.parametrize(
    ("alphabet_id", "expected"),
    [
        (
            "ru",
            {
                "code": "a",
                "symbol": "А",
                "kind": "vowel",
                "image_url": None,
                "sound_url": None,
                "words": [
                    {"text": text, "image_url": None, "sound_url": None}
                    for text in ("арбуз", "автобус", "ананас")
                ],
            },
        ),
        (
            "en",
            {
                "code": "a",
                "symbol": "A",
                "kind": "vowel",
                "image_url": None,
                "sound_url": None,
                "words": [{"text": "apple", "image_url": None, "sound_url": None}],
            },
        ),
    ],
)
async def test_get_letter_returns_words(
    api_client: AsyncClient, alphabet_id: str, expected: dict[str, object]
) -> None:
    response = await api_client.get(f"/api/v1/alphabets/{alphabet_id}/letters/a")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == expected


async def test_get_letter_returns_media_urls(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/alphabets/ru/letters/m")

    assert response.status_code == 200
    assert response.json() == {
        "code": "m",
        "symbol": "М",
        "kind": "consonant",
        "image_url": media_url("letters/m.webp"),
        "sound_url": media_url("letters/m.mp3"),
        "words": [
            {
                "text": "мяч",
                "image_url": media_url("words/myach.webp"),
                "sound_url": media_url("words/myach.mp3"),
            },
            {"text": "машина", "image_url": None, "sound_url": None},
        ],
    }


@pytest.mark.parametrize(
    ("alphabet_id", "code"),
    [
        pytest.param("de", "a", id="unknown-alphabet"),
        pytest.param("ru", "z", id="unknown-code"),
        pytest.param("en", "m", id="other-alphabet"),
    ],
)
async def test_unknown_letter_returns_not_found(
    api_client: AsyncClient, alphabet_id: str, code: str
) -> None:
    response = await api_client.get(f"/api/v1/alphabets/{alphabet_id}/letters/{code}")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json()["detail"] == "Alphabet or letter not found"
