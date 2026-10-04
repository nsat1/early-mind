from typing import Literal

from pydantic import BaseModel


class LetterSummary(BaseModel):
    id: str
    symbol: str
    kind: Literal["vowel", "consonant", "sign"]


class LetterResponse(LetterSummary):
    words: list[str]
