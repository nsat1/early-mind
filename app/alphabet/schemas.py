from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.alphabet.models import LetterKind


class LetterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: Annotated[
        str,
        Field(description="Код буквы латиницей, уникален в алфавите", examples=["m"]),
    ]
    symbol: Annotated[str, Field(description="Заглавная буква", examples=["М"])]
    kind: Annotated[
        LetterKind,
        Field(
            description="Вид буквы: гласная, согласная или знак",
            examples=["consonant"],
        ),
    ]


class LetterDetail(LetterSummary):
    words: Annotated[
        list[str],
        Field(
            description="Слова-примеры в порядке показа",
            examples=[["мяч", "машина", "медведь"]],
        ),
    ]
