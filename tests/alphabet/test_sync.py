import logging
from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alphabet.models import Letter, LetterKind
from app.alphabet.source import (
    CONTENT_DIR,
    AlphabetSource,
    LetterSource,
    WordSource,
    load_alphabet,
)
from app.alphabet.sync import SyncResult, main, sync_alphabet

pytestmark = [pytest.mark.integration, pytest.mark.anyio]

Snapshot = list[tuple[str, str, LetterKind, int, list[str]]]


def words(*texts: str) -> list[WordSource]:
    return [WordSource(text=text) for text in texts]


A = LetterSource(
    code="a",
    symbol="А",
    kind=LetterKind.VOWEL,
    position=1,
    words=words("арбуз", "аист"),
)
B = LetterSource(
    code="b", symbol="Б", kind=LetterKind.CONSONANT, position=2, words=words("банан")
)
ALPHABET = AlphabetSource(id="ru", letters=[A, B])
RUSSIAN = CONTENT_DIR / "ru.toml"


def snapshot(source: AlphabetSource) -> Snapshot:
    return [
        (
            letter.code,
            letter.symbol,
            letter.kind,
            letter.position,
            [word.text for word in letter.words],
        )
        for letter in sorted(source.letters, key=lambda letter: letter.position)
    ]


async def stored(session: AsyncSession, alphabet_id: str) -> Snapshot:
    letters = await session.scalars(
        select(Letter)
        .where(Letter.alphabet_id == alphabet_id)
        .order_by(Letter.position)
        .options(selectinload(Letter.words))
        .execution_options(populate_existing=True)
    )
    return [
        (
            letter.code,
            letter.symbol,
            letter.kind,
            letter.position,
            [word.example for word in letter.words],
        )
        for letter in letters
    ]


async def letter_ids(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(select(Letter.code, Letter.letter_id))
    return {code: letter_id for code, letter_id in rows}


def count_words(source: AlphabetSource) -> int:
    return sum(len(letter.words) for letter in source.letters)


def expected_result(source: AlphabetSource, changed: int, removed: int) -> SyncResult:
    return SyncResult(
        alphabet_id=source.id,
        letters=len(source.letters),
        words=count_words(source),
        changed=changed,
        removed=removed,
    )


async def test_sync_loads_content_file(db_session: AsyncSession) -> None:
    source = load_alphabet(RUSSIAN)

    result = await sync_alphabet(db_session, source)

    rows = 1 + len(source.letters) + count_words(source)
    assert result == expected_result(source, changed=rows, removed=0)
    assert await stored(db_session, "ru") == snapshot(source)


async def test_repeated_sync_changes_nothing(db_session: AsyncSession) -> None:
    await sync_alphabet(db_session, ALPHABET)
    ids = await letter_ids(db_session)

    result = await sync_alphabet(db_session, ALPHABET)

    assert result == expected_result(ALPHABET, changed=0, removed=0)
    assert await letter_ids(db_session) == ids


async def test_sync_applies_changes(db_session: AsyncSession) -> None:
    await sync_alphabet(db_session, ALPHABET)
    ids = await letter_ids(db_session)
    changed = AlphabetSource(
        id="ru",
        letters=[
            A.model_copy(update={"words": words("аист")}),
            B.model_copy(update={"kind": LetterKind.VOWEL}),
            LetterSource(
                code="v",
                symbol="В",
                kind=LetterKind.CONSONANT,
                position=3,
                words=words("вол"),
            ),
        ],
    )

    result = await sync_alphabet(db_session, changed)

    assert result == expected_result(changed, changed=4, removed=1)
    assert await stored(db_session, "ru") == snapshot(changed)
    assert ids.items() <= (await letter_ids(db_session)).items()


async def test_sync_keeps_letters_missing_from_content(
    db_session: AsyncSession, caplog: pytest.LogCaptureFixture
) -> None:
    await sync_alphabet(db_session, ALPHABET)
    reduced = AlphabetSource(id="ru", letters=[A])

    with caplog.at_level(logging.WARNING, logger="app.alphabet.sync"):
        result = await sync_alphabet(db_session, reduced)

    assert result == expected_result(reduced, changed=0, removed=0)
    assert await stored(db_session, "ru") == snapshot(ALPHABET)
    assert caplog.messages == ["ru: letters missing from content: b"]


async def test_sync_rejects_swapped_positions(db_session: AsyncSession) -> None:
    await sync_alphabet(db_session, ALPHABET)
    swapped = AlphabetSource(
        id="ru",
        letters=[
            A.model_copy(update={"position": B.position}),
            B.model_copy(update={"position": A.position}),
        ],
    )

    with pytest.raises(IntegrityError) as raised:
        async with db_session.begin_nested():
            await sync_alphabet(db_session, swapped)

    assert raised.value.orig.diag.constraint_name == "uq_letters_alphabet_id_position"
    assert await stored(db_session, "ru") == snapshot(ALPHABET)


@pytest.fixture
def cleanup_content(app_connection: psycopg.Connection) -> Iterator[psycopg.Connection]:
    yield app_connection
    app_connection.execute("DELETE FROM alphabets")


def test_main_commits_content(
    cleanup_content: psycopg.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    source = load_alphabet(RUSSIAN)

    with caplog.at_level(logging.INFO, logger="app.alphabet.sync"):
        main()

    counts = cleanup_content.execute(
        "SELECT (SELECT count(*) FROM letters), (SELECT count(*) FROM words)"
    ).fetchone()
    rows = 1 + len(source.letters) + count_words(source)
    assert counts == (len(source.letters), count_words(source))
    assert caplog.messages == [str(expected_result(source, changed=rows, removed=0))]
