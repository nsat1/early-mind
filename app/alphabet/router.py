from fastapi import APIRouter, HTTPException

from app.alphabet.content import LETTERS
from app.alphabet.schemas import LetterResponse

router = APIRouter(prefix="/api/v1/alphabets", tags=["alphabet"])


@router.get(
    "/{alphabet_id}/letters/{letter_id}", responses={404: {"description": "Not found"}}
)
async def get_letter(alphabet_id: str, letter_id: str) -> LetterResponse:
    letter = LETTERS.get(alphabet_id, {}).get(letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Alphabet or letter not found")
    return LetterResponse.model_validate(letter)
