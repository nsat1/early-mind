import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import (
    DATABASE_UNAVAILABLE,
    SESSION_STORAGE_UNAVAILABLE,
    problem_responses,
)
from app.db.dependencies import DbSession, RedisClient

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
    description=(
        "Проверяет БД и хранилище сессий Redis, отвечает 503, если одно из них "
        "недоступно."
    ),
    response_description="API готов",
    responses=problem_responses(
        {
            503: (
                "API не готов: база данных или хранилище сессий недоступны",
                DATABASE_UNAVAILABLE,
            )
        }
    ),
)
async def check_readiness(session: DbSession, redis: RedisClient) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Database readiness check failed", exc_info=True)
        raise HTTPException(status_code=503, detail=DATABASE_UNAVAILABLE) from None
    try:
        await redis.ping()
    except RedisError:
        logger.warning("Session storage readiness check failed", exc_info=True)
        raise HTTPException(
            status_code=503, detail=SESSION_STORAGE_UNAVAILABLE
        ) from None
    return HealthResponse(status="ok")
