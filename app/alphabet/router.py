from fastapi import APIRouter, HTTPException

from app.alphabet.content import LETTERS
from app.alphabet.schemas import LetterResponse, LetterSummary

router = APIRouter(prefix="/api/v1/alphabets", tags=["alphabet"])


@router.get("/{alphabet_id}/letters", responses={404: {"description": "Not found"}})
async def list_letters(alphabet_id: str) -> list[LetterSummary]:
    alphabet = LETTERS.get(alphabet_id)
    if alphabet is None:
        raise HTTPException(status_code=404, detail="Alphabet not found")
    return [LetterSummary.model_validate(letter) for letter in alphabet.values()]


@router.get(
    "/{alphabet_id}/letters/{letter_id}", responses={404: {"description": "Not found"}}
)
async def get_letter(alphabet_id: str, letter_id: str) -> LetterResponse:
    letter = LETTERS.get(alphabet_id, {}).get(letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Alphabet or letter not found")
    return LetterResponse.model_validate(letter)
