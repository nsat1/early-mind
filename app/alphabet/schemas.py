from pydantic import BaseModel


class LetterResponse(BaseModel):
    id: str
    symbol: str
    words: list[str]
