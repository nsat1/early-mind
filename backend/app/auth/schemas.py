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


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Registration(StrictModel):
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


class VerificationResend(StrictModel):
    email: Email


class Login(StrictModel):
    email: Email
    password: Annotated[
        str, Field(description="Пароль аккаунта", examples=["мама мыла раму 7"])
    ]


class EmailVerification(StrictModel):
    token: Annotated[
        str,
        Field(
            max_length=64,
            description="Токен из ссылки в письме — часть после `#token=`",
            examples=["f_i7GrgiEQEbg0VS0YT9XZtpDpXRbFBsnqDbI8JQDUI"],
        ),
    ]
