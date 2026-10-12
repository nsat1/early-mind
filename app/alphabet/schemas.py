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


MediaUrl = Annotated[
    str | None,
    Field(
        description="Адрес файла с версией. Пусто, если файла ещё нет",
        examples=["/media/ru/letters/m.mp3?v=3fa2c1d4"],
    ),
]


class WordExample(BaseModel):
    text: Annotated[str, Field(description="Слово", examples=["медведь"])]
    image_url: MediaUrl
    sound_url: MediaUrl


class LetterDetail(LetterSummary):
    sound_url: MediaUrl
    words: Annotated[
        list[WordExample], Field(description="Слова-примеры в порядке показа")
    ]
