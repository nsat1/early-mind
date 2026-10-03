from pydantic import BaseModel


class LetterSummary(BaseModel):
    id: str
    symbol: str


class LetterResponse(LetterSummary):
    words: list[str]
