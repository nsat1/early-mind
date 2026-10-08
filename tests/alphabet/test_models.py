from collections.abc import Iterator

import psycopg
import pytest
from psycopg import errors
from sqlalchemy import select, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import selectinload

from app.alphabet.models import Alphabet, Letter, LetterKind, Word
from app.core.config import Settings
from app.db.session import create_database

pytestmark = pytest.mark.integration

INSERT_LETTER = (
    "INSERT INTO letters (alphabet_id, code, symbol, kind, position) "
    "VALUES (%s, %s, %s, %s, %s)"
)


@pytest.fixture
def content(app_connection: psycopg.Connection) -> Iterator[psycopg.Connection]:
    with app_connection.transaction(force_rollback=True):
        app_connection.execute("INSERT INTO alphabets (id) VALUES ('ru')")
        app_connection.execute(INSERT_LETTER, ("ru", "a", "А", "vowel", 1))
        yield app_connection


@pytest.mark.parametrize(
    ("values", "constraint"),
    [
        (("ru", "a", "А", "vowel", 2), "uq_letters_alphabet_id_code"),
        (("ru", "b", "Б", "consonant", 1), "uq_letters_alphabet_id_position"),
        (("ru", "b", "Б", "letter", 2), "ck_letters_kind"),
        (("ru", "b", "Б", "consonant", 0), "ck_letters_position_positive"),
        (("en", "b", "B", "consonant", 2), "fk_letters_alphabet_id_alphabets"),
    ],
)
def test_database_rejects_invalid_letter(
    content: psycopg.Connection, values: tuple[object, ...], constraint: str
) -> None:
    with pytest.raises(errors.IntegrityError) as raised:
        content.execute(INSERT_LETTER, values)
    assert raised.value.diag.constraint_name == constraint


def test_database_rejects_invalid_word_position(content: psycopg.Connection) -> None:
    with pytest.raises(errors.CheckViolation) as raised:
        content.execute(
            "INSERT INTO words (letter_id, text, position) "
            "SELECT id, 'арбуз', 0 FROM letters"
        )
    assert raised.value.diag.constraint_name == "ck_words_position_positive"


def test_deleting_letter_deletes_its_words(content: psycopg.Connection) -> None:
    content.execute(
        "INSERT INTO words (letter_id, text, position) SELECT id, 'арбуз', 1 FROM letters"
    )
    content.execute("DELETE FROM letters")
    assert content.execute("SELECT count(*) FROM words").fetchone() == (0,)


@pytest.mark.anyio
async def test_letter_round_trip(test_database: None) -> None:
    engine, sessions = create_database(Settings())
    try:
        async with sessions() as session:
            session.add(Alphabet(id="ru"))
            session.add(
                Letter(
                    alphabet_id="ru",
                    code="a",
                    symbol="А",
                    kind=LetterKind.VOWEL,
                    position=1,
                    words=[
                        Word(text="ананас", position=2),
                        Word(text="арбуз", position=1),
                    ],
                )
            )
            await session.flush()
            session.expunge_all()

            stored_kind = await session.scalar(text("SELECT kind FROM letters"))
            letter = await session.scalar(
                select(Letter).options(selectinload(Letter.words))
            )
            session.expunge_all()
            unloaded = await session.scalar(select(Letter))
    finally:
        await engine.dispose()

    assert stored_kind == "vowel"
    assert letter is not None
    assert letter.kind is LetterKind.VOWEL
    assert [word.text for word in letter.words] == ["арбуз", "ананас"]
    assert unloaded is not None
    with pytest.raises(InvalidRequestError, match="lazy='raise'"):
        _ = unloaded.words
