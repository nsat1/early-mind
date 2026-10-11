import pytest
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.alphabet.models import LetterKind
from app.alphabet.source import AlphabetSource, LetterSource
from app.alphabet.sync import sync_alphabet
from app.core.errors import PROBLEM_MEDIA_TYPE

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

RUSSIAN = AlphabetSource(
    id="ru",
    letters=[
        LetterSource(
            code="soft", symbol="Ь", kind=LetterKind.SIGN, position=30, words=["конь"]
        ),
        LetterSource(
            code="m",
            symbol="М",
            kind=LetterKind.CONSONANT,
            position=14,
            words=["мяч", "машина"],
        ),
        LetterSource(
            code="a",
            symbol="А",
            kind=LetterKind.VOWEL,
            position=1,
            words=["арбуз", "автобус", "ананас"],
        ),
        LetterSource(
            code="yo", symbol="Ё", kind=LetterKind.VOWEL, position=7, words=["ёж"]
        ),
    ],
)
ENGLISH = AlphabetSource(
    id="en",
    letters=[
        LetterSource(
            code="a", symbol="A", kind=LetterKind.VOWEL, position=1, words=["apple"]
        )
    ],
)


@pytest.fixture(autouse=True)
async def alphabets(db_session: AsyncSession) -> None:
    for source in (RUSSIAN, ENGLISH):
        await sync_alphabet(db_session, source)


async def test_list_letters_orders_by_position(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/alphabets/ru/letters")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == [
        {"code": "a", "symbol": "А", "kind": "vowel"},
        {"code": "yo", "symbol": "Ё", "kind": "vowel"},
        {"code": "m", "symbol": "М", "kind": "consonant"},
        {"code": "soft", "symbol": "Ь", "kind": "sign"},
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
                "words": ["арбуз", "автобус", "ананас"],
            },
        ),
        ("en", {"code": "a", "symbol": "A", "kind": "vowel", "words": ["apple"]}),
    ],
)
async def test_get_letter_returns_words(
    api_client: AsyncClient, alphabet_id: str, expected: dict[str, object]
) -> None:
    response = await api_client.get(f"/api/v1/alphabets/{alphabet_id}/letters/a")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == expected


@pytest.mark.parametrize(
    ("alphabet_id", "code"),
    [
        pytest.param("de", "a", id="unknown-alphabet"),
        pytest.param("ru", "z", id="unknown-code"),
        pytest.param("en", "m", id="other-alphabet"),
        pytest.param("ru", "а", id="cyrillic-code"),
    ],
)
async def test_unknown_letter_returns_not_found(
    api_client: AsyncClient, alphabet_id: str, code: str
) -> None:
    response = await api_client.get(f"/api/v1/alphabets/{alphabet_id}/letters/{code}")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json()["detail"] == "Alphabet or letter not found"
