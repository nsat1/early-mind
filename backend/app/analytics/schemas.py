from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.alphabet.source import AlphabetId, LetterCode
from app.analytics.models import APP_VERSION_LENGTH, AnalyticsEventName

MAX_BATCH_SIZE = 50
LETTERS_IN_ALPHABET = 33

Count = Annotated[int, Field(ge=0)]
LetterCount = Annotated[int, Field(ge=0, le=LETTERS_IN_ALPHABET)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class AppOpenedProperties(StrictModel):
    days_since_first_visit: Annotated[
        Literal["0", "1", "2-6", "7-13", "14-29", "30+"],
        Field(description="Диапазон дней с первого визита"),
    ]
    first_visit_week: Annotated[
        str,
        StringConstraints(pattern=r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$"),
        Field(
            description="Неделя первого визита по ISO 8601 — когорта",
            examples=["2026-W42"],
        ),
    ]


class SessionFinishedProperties(StrictModel):
    duration_seconds: Annotated[
        int,
        Field(
            ge=0,
            le=7200,
            multiple_of=10,
            description="Длительность сессии без бездействия, округлена до 10 секунд",
            examples=[420],
        ),
    ]
    cards_opened: Annotated[
        Count, Field(description="Число открытий карточек букв", examples=[6])
    ]
    answers: Annotated[Count, Field(description="Число ответов", examples=[10])]
    correct_answers: Annotated[
        Count, Field(description="Число верных ответов", examples=[8])
    ]
    learned_letters: Annotated[
        LetterCount, Field(description="Число изученных букв", examples=[12])
    ]
    strong_letters: Annotated[
        LetterCount, Field(description="Число сильных букв", examples=[5])
    ]

    @model_validator(mode="after")
    def check_counts(self) -> Self:
        if self.correct_answers > self.answers:
            raise ValueError("correct_answers must not exceed answers")
        if self.strong_letters > self.learned_letters:
            raise ValueError("strong_letters must not exceed learned_letters")
        return self


class AnswerGivenProperties(StrictModel):
    alphabet_id: Annotated[
        AlphabetId, Field(description="Алфавит задания", examples=["ru"])
    ]
    letter_code: Annotated[
        LetterCode,
        Field(description="Буква, которую нужно было найти", examples=["m"]),
    ]
    task_type: Annotated[
        Literal["sound", "picture"],
        Field(description="Тип задания: по звуку или по картинке"),
    ]
    correct: Annotated[bool, Field(description="Верный ли ответ")]


class EventEnvelope(StrictModel):
    schema_version: Annotated[
        Literal[1], Field(description="Версия схемы полей события")
    ]
    app_version: Annotated[
        str,
        StringConstraints(min_length=1, max_length=APP_VERSION_LENGTH),
        Field(description="Версия веб-приложения", examples=["1.0.0"]),
    ]


class AppOpened(EventEnvelope):
    name: Literal[AnalyticsEventName.APP_OPENED]
    properties: AppOpenedProperties


class SessionFinished(EventEnvelope):
    name: Literal[AnalyticsEventName.SESSION_FINISHED]
    properties: SessionFinishedProperties


class AnswerGiven(EventEnvelope):
    name: Literal[AnalyticsEventName.ANSWER_GIVEN]
    properties: AnswerGivenProperties


AnalyticsEventIn = Annotated[
    AppOpened | SessionFinished | AnswerGiven, Field(discriminator="name")
]
