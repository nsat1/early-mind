from typing import Annotated

from pydantic import BaseModel, Field

from app.alphabet.models import LetterKind

SoundUrl = Annotated[
    str | None,
    Field(
        description="Адрес звука с версией. Пусто, если файла ещё нет",
        examples=["/media/ru/letters/m.mp3?v=3fa2c1d4"],
    ),
]
ImageUrl = Annotated[
    str | None,
    Field(
        description="Адрес картинки с версией. Пусто, если файла ещё нет",
        examples=["/media/ru/letters/m.webp?v=9d41b7e2"],
    ),
]


class LetterSummary(BaseModel):
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
    image_url: ImageUrl


class WordExample(BaseModel):
    text: Annotated[str, Field(description="Слово", examples=["медведь"])]
    image_url: Annotated[
        ImageUrl, Field(examples=["/media/ru/words/medved.webp?v=5b9e0a17"])
    ]
    sound_url: Annotated[
        SoundUrl, Field(examples=["/media/ru/words/medved.mp3?v=8c2d4f60"])
    ]


class LetterDetail(LetterSummary):
    sound_url: SoundUrl
    words: Annotated[
        list[WordExample], Field(description="Слова-примеры в порядке показа")
    ]
