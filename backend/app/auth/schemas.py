from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

PRIVACY_POLICY_VERSION = "2026-10-16"

Email = Annotated[
    EmailStr,
    AfterValidator(str.lower),
    Field(
        description="Email родителя, сравнивается без учёта регистра",
        examples=["anna.petrova@mail.ru"],
    ),
]


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    email: Email
    password: Annotated[
        str,
        Field(
            description=(
                "От 8 до 64 символов, любые символы. Не из списка частых паролей "
                "и не совпадает с email"
            ),
            examples=["мама мыла раму 7"],
        ),
    ]
    policy_version: Annotated[
        Literal[PRIVACY_POLICY_VERSION],
        Field(description="Версия политики обработки персональных данных"),
    ]
    consent: Annotated[
        Literal[True],
        Field(description="Согласие на обработку персональных данных"),
    ]
    adult: Annotated[Literal[True], Field(description="Родителю есть 18 лет")]
