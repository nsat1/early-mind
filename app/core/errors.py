import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
INVALID_PARAMETERS = "Request parameters are invalid"
DATABASE_UNAVAILABLE = "Database unavailable"
COMMON_PROBLEMS = {
    422: ("Параметры запроса не прошли проверку", INVALID_PARAMETERS),
    503: ("База данных недоступна", DATABASE_UNAVAILABLE),
}


class ParameterError(BaseModel):
    location: Annotated[
        str,
        Field(
            serialization_alias="in",
            description="Где передан параметр: `path` или `query`",
            examples=["path"],
        ),
    ]
    name: Annotated[str, Field(description="Имя параметра", examples=["alphabet_id"])]
    detail: Annotated[
        str,
        Field(
            description="Что не так со значением",
            examples=["String should match pattern '^[a-z]+$'"],
        ),
    ]


class Problem(BaseModel):
    type: Annotated[
        str,
        Field(description="Тип ошибки. `about:blank` — смысл передаёт HTTP-статус"),
    ] = "about:blank"
    title: Annotated[
        str, Field(description="Название HTTP-статуса", examples=["Not Found"])
    ]
    status: Annotated[int, Field(description="HTTP-статус", examples=[404])]
    detail: Annotated[
        str | None,
        Field(description="Описание этого случая", examples=["Alphabet not found"]),
    ] = None
    instance: Annotated[
        str | None,
        Field(description="Путь запроса", examples=["/api/v1/alphabets/de/letters"]),
    ] = None
    errors: Annotated[
        list[ParameterError] | None,
        Field(description="Ошибки параметров, только для ответа 422"),
    ] = None


def problem_example(status: int, detail: str) -> dict[str, Any]:
    errors = None
    if status == 422:
        errors = [
            ParameterError(
                location="path",
                name="alphabet_id",
                detail="String should match pattern '^[a-z]+$'",
            )
        ]
    problem = Problem(
        title=HTTPStatus(status).phrase, status=status, detail=detail, errors=errors
    )
    return problem.model_dump(by_alias=True, exclude_none=True)


def problem_responses(
    problems: dict[int, tuple[str, str]],
) -> dict[int | str, dict[str, Any]]:
    return {
        status: {
            "model": Problem,
            "description": description,
            "content": {
                "application/json": {"example": problem_example(status, detail)}
            },
        }
        for status, (description, detail) in problems.items()
    }


def problem_response(
    request: Request,
    status: int,
    detail: str | None = None,
    errors: list[ParameterError] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = Problem(
        title=HTTPStatus(status).phrase,
        status=status,
        detail=detail,
        instance=request.url.path,
        errors=errors,
    )
    return JSONResponse(
        problem.model_dump(by_alias=True, exclude_none=True),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    detail = str(exc.detail)
    if detail == HTTPStatus(exc.status_code).phrase:
        detail = None
    return problem_response(request, exc.status_code, detail, headers=exc.headers)


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        ParameterError(
            location=str(error["loc"][0]),
            name=".".join(str(part) for part in error["loc"][1:]),
            detail=error["msg"],
        )
        for error in exc.errors()
    ]
    return problem_response(request, 422, INVALID_PARAMETERS, errors=errors)


async def handle_database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    logger.warning("Database unavailable", exc_info=exc)
    return problem_response(request, 503, DATABASE_UNAVAILABLE)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(request, 500)


def problem_openapi(
    build: Callable[[], dict[str, Any]],
) -> Callable[[], dict[str, Any]]:
    def openapi() -> dict[str, Any]:
        schema = build()
        for path in schema["paths"].values():
            for operation in path.values():
                for status, response in operation["responses"].items():
                    content = response.get("content", {})
                    if status[0] in "45" and "application/json" in content:
                        content[PROBLEM_MEDIA_TYPE] = content.pop("application/json")
        return schema

    return openapi


def register_problem_details(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(OperationalError, handle_database_unavailable)
    app.add_exception_handler(PoolTimeoutError, handle_database_unavailable)
    app.add_exception_handler(Exception, handle_unexpected_error)
    app.openapi = problem_openapi(app.openapi)
