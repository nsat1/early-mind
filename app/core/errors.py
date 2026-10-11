import logging
from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"


class ParameterError(BaseModel):
    location: str = Field(serialization_alias="in")
    name: str
    detail: str


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[ParameterError] | None = None


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {status: {"model": Problem} for status in statuses}


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
    return problem_response(
        request, 422, "Request parameters are invalid", errors=errors
    )


async def handle_database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    logger.warning("Database unavailable", exc_info=exc)
    return problem_response(request, 503, "Database unavailable")


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
