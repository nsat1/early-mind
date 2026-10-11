from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.alphabet.models import Alphabet, Letter, LetterKind


async def list_letters(
    session: AsyncSession, alphabet_id: str, kind: LetterKind | None = None
) -> Sequence[Letter] | None:
    if await session.get(Alphabet, alphabet_id) is None:
        return None
    statement = (
        select(Letter)
        .where(Letter.alphabet_id == alphabet_id)
        .order_by(Letter.position)
    )
    if kind is not None:
        statement = statement.where(Letter.kind == kind)
    return (await session.scalars(statement)).all()


async def get_letter(
    session: AsyncSession, alphabet_id: str, code: str
) -> Letter | None:
    return await session.scalar(
        select(Letter)
        .where(Letter.alphabet_id == alphabet_id, Letter.code == code)
        .options(selectinload(Letter.words))
    )
