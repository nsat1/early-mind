from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.alphabet import repository
from app.alphabet.media import media_url
from app.alphabet.models import LetterKind
from app.alphabet.schemas import LetterDetail, LetterSummary, WordExample
from app.alphabet.source import AlphabetId, LetterCode
from app.core.errors import COMMON_PROBLEMS, problem_responses
from app.db.dependencies import DbSession

router = APIRouter(prefix="/api/v1/alphabets", tags=["alphabet"])

ALPHABET_NOT_FOUND = "Alphabet not found"
LETTER_NOT_FOUND = "Alphabet or letter not found"

AlphabetPath = Annotated[
    AlphabetId,
    Path(
        description="Код алфавита, пример - ru (код языка по ISO 639-1)",
        examples=["ru"],
    ),
]
CodePath = Annotated[
    LetterCode,
    Path(description="Код буквы латиницей, например `a` или `zh`", examples=["m"]),
]
KindQuery = Annotated[
    LetterKind | None,
    Query(
        description=(
            "Вид букв: `vowel` — гласные, `consonant` — согласные, "
            "`sign` — знаки. Без фильтра — все буквы"
        )
    ),
]


@router.get(
    "/{alphabet_id}/letters",
    summary="Список букв алфавита",
    description=(
        "Буквы в порядке позиции в алфавите. Фильтр `kind` оставляет буквы "
        "одного вида; если таких нет — пустой список."
    ),
    response_description="Буквы алфавита",
    responses=problem_responses(
        {404: ("Алфавит не найден", ALPHABET_NOT_FOUND)} | COMMON_PROBLEMS
    ),
)
async def list_letters(
    session: DbSession, alphabet_id: AlphabetPath, kind: KindQuery = None
) -> list[LetterSummary]:
    letters = await repository.list_letters(session, alphabet_id, kind)
    if letters is None:
        raise HTTPException(status_code=404, detail=ALPHABET_NOT_FOUND)
    return [LetterSummary.model_validate(letter) for letter in letters]


@router.get(
    "/{alphabet_id}/letters/{code}",
    summary="Буква со словами-примерами",
    description="Буква по коду вместе со словами-примерами в порядке показа.",
    response_description="Буква",
    responses=problem_responses(
        {404: ("Алфавит или буква не найдены", LETTER_NOT_FOUND)} | COMMON_PROBLEMS
    ),
)
async def get_letter(
    session: DbSession, alphabet_id: AlphabetPath, code: CodePath
) -> LetterDetail:
    letter = await repository.get_letter(session, alphabet_id, code)
    if letter is None:
        raise HTTPException(status_code=404, detail=LETTER_NOT_FOUND)
    return LetterDetail(
        code=letter.code,
        symbol=letter.symbol,
        kind=letter.kind,
        sound_url=media_url(alphabet_id, letter.sound),
        words=[
            WordExample(
                text=word.example,
                image_url=media_url(alphabet_id, word.image),
                sound_url=media_url(alphabet_id, word.sound),
            )
            for word in letter.words
        ],
    )
