from pydantic import BaseModel, ConfigDict

from app.alphabet.models import LetterKind


class LetterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    symbol: str
    kind: LetterKind


class LetterDetail(LetterSummary):
    words: list[str]
