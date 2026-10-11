import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import DATABASE_UNAVAILABLE, problem_responses
from app.db.dependencies import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Annotated[Literal["ok"], Field(description="Проверка пройдена")]


@router.get(
    "/health",
    summary="Процесс API работает",
    description="Отвечает, пока процесс запущен. БД не проверяется.",
    response_description="Процесс работает",
)
async def check_health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/health/ready",
    summary="API готов принимать запросы",
    description="Выполняет запрос к БД и отвечает 503, если БД недоступна.",
    response_description="API готов",
    responses=problem_responses(
        {503: ("API не готов: база данных недоступна", DATABASE_UNAVAILABLE)}
    ),
)
async def check_readiness(session: DbSession) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Database readiness check failed", exc_info=True)
        raise HTTPException(status_code=503, detail=DATABASE_UNAVAILABLE) from None
    return HealthResponse(status="ok")
