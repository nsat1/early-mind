import asyncio
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Executable, delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.alphabet.models import MEDIA_VERSION_LENGTH, Alphabet, Letter, Word
from app.alphabet.source import (
    CONTENT_DIR,
    AlphabetSource,
    LetterSource,
    alphabet_files,
    load_alphabet,
    media_problems,
)
from app.core.config import Settings
from app.db.session import create_database

logger = logging.getLogger(__name__)

LETTER_FIELDS = ("symbol", "kind", "position", "sound")
WORD_FIELDS = ("example", "image", "sound")


@dataclass(frozen=True, slots=True)
class SyncResult:
    alphabet_id: str
    letters: int
    words: int
    changed: int
    removed: int

    def __str__(self) -> str:
        return (
            f"{self.alphabet_id}: {self.letters} letters, {self.words} words; "
            f"{self.changed} rows changed, {self.removed} words removed"
        )


async def count_rows(session: AsyncSession, statement: Executable) -> int:
    return len((await session.scalars(statement)).all())


def versioned(files: Path, path: str | None) -> str | None:
    if path is None:
        return None
    digest = hashlib.sha256((files / path).read_bytes()).hexdigest()
    return f"{path}?v={digest[:MEDIA_VERSION_LENGTH]}"


def letter_row(letter: LetterSource, files: Path) -> dict[str, Any]:
    return {
        "code": letter.code,
        "symbol": letter.symbol,
        "kind": letter.kind,
        "position": letter.position,
        "sound": versioned(files, letter.sound),
    }


async def sync_alphabet(
    session: AsyncSession, source: AlphabetSource, alphabet_dir: Path | None = None
) -> SyncResult:
    files = alphabet_dir if alphabet_dir is not None else CONTENT_DIR / source.id
    problems = media_problems(source, files)
    if problems:
        raise ValueError(f"{source.id}: invalid media: {'; '.join(problems)}")

    changed = await count_rows(
        session,
        insert(Alphabet)
        .values(alphabet_id=source.id)
        .on_conflict_do_nothing()
        .returning(Alphabet.alphabet_id),
    )

    letters = insert(Letter).values(
        [
            {"alphabet_id": source.id, **letter_row(letter, files)}
            for letter in source.letters
        ]
    )
    changed += await count_rows(
        session,
        letters.on_conflict_do_update(
            index_elements=[Letter.alphabet_id, Letter.code],
            set_={field: letters.excluded[field] for field in LETTER_FIELDS},
            where=tuple_(
                *(getattr(Letter, field) for field in LETTER_FIELDS)
            ).is_distinct_from(
                tuple_(*(letters.excluded[field] for field in LETTER_FIELDS))
            ),
        ).returning(Letter.letter_id),
    )

    stored = await session.execute(
        select(Letter.code, Letter.letter_id).where(Letter.alphabet_id == source.id)
    )
    letter_ids = {code: letter_id for code, letter_id in stored}
    missing = sorted(letter_ids.keys() - {letter.code for letter in source.letters})
    if missing:
        logger.warning(
            "%s: letters missing from content: %s", source.id, ", ".join(missing)
        )

    kept = [
        {
            "letter_id": letter_ids[letter.code],
            "position": position,
            "example": word.text,
            "image": versioned(files, word.image),
            "sound": versioned(files, word.sound),
        }
        for letter in source.letters
        for position, word in enumerate(letter.words, start=1)
    ]
    words = insert(Word).values(kept)
    changed += await count_rows(
        session,
        words.on_conflict_do_update(
            index_elements=[Word.letter_id, Word.position],
            set_={field: words.excluded[field] for field in WORD_FIELDS},
            where=tuple_(
                *(getattr(Word, field) for field in WORD_FIELDS)
            ).is_distinct_from(
                tuple_(*(words.excluded[field] for field in WORD_FIELDS))
            ),
        ).returning(Word.word_id),
    )
    removed = await count_rows(
        session,
        delete(Word)
        .where(
            Word.letter_id.in_({word["letter_id"] for word in kept}),
            tuple_(Word.letter_id, Word.position).not_in(
                [(word["letter_id"], word["position"]) for word in kept]
            ),
        )
        .returning(Word.word_id)
        .execution_options(synchronize_session=False),
    )

    return SyncResult(
        alphabet_id=source.id,
        letters=len(source.letters),
        words=len(kept),
        changed=changed,
        removed=removed,
    )


async def sync_content(
    settings: Settings, content_dir: Path = CONTENT_DIR
) -> list[SyncResult]:
    sources = [
        (load_alphabet(path), path.parent) for path in alphabet_files(content_dir)
    ]
    engine, sessions = create_database(settings)
    try:
        async with sessions.begin() as session:
            return [
                await sync_alphabet(session, source, alphabet_dir)
                for source, alphabet_dir in sources
            ]
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    results = asyncio.run(
        sync_content(Settings()), loop_factory=asyncio.SelectorEventLoop
    )
    for result in results:
        logger.info("%s", result)


if __name__ == "__main__":
    main()
