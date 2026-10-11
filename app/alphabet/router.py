from fastapi import APIRouter, HTTPException

from app.alphabet import repository
from app.alphabet.models import LetterKind
from app.alphabet.schemas import LetterDetail, LetterSummary
from app.core.errors import problem_responses
from app.db.dependencies import DbSession

router = APIRouter(prefix="/api/v1/alphabets", tags=["alphabet"])


@router.get("/{alphabet_id}/letters", responses=problem_responses(404, 422, 503))
async def list_letters(
    session: DbSession, alphabet_id: str, kind: LetterKind | None = None
) -> list[LetterSummary]:
    letters = await repository.list_letters(session, alphabet_id, kind)
    if letters is None:
        raise HTTPException(status_code=404, detail="Alphabet not found")
    return [LetterSummary.model_validate(letter) for letter in letters]


@router.get("/{alphabet_id}/letters/{code}", responses=problem_responses(404, 422, 503))
async def get_letter(session: DbSession, alphabet_id: str, code: str) -> LetterDetail:
    letter = await repository.get_letter(session, alphabet_id, code)
    if letter is None:
        raise HTTPException(status_code=404, detail="Alphabet or letter not found")
    return LetterDetail(
        code=letter.code,
        symbol=letter.symbol,
        kind=letter.kind,
        words=[word.example for word in letter.words],
    )
