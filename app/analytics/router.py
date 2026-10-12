from typing import Annotated

from fastapi import APIRouter, Body, Response
from sqlalchemy import insert

from app.analytics.models import AnalyticsEvent
from app.analytics.schemas import MAX_BATCH_SIZE, AnalyticsEventIn
from app.core.errors import COMMON_PROBLEMS, problem_responses
from app.db.dependencies import DbSession

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

EventBatch = Annotated[
    list[AnalyticsEventIn],
    Body(
        min_length=1,
        max_length=MAX_BATCH_SIZE,
        description=(
            f"Пачка от 1 до {MAX_BATCH_SIZE} событий по каталогу аналитики. "
            "Тип содержимого — `application/json`, в том числе при отправке "
            "через `navigator.sendBeacon`."
        ),
    ),
]


@router.post(
    "/events",
    status_code=202,
    response_class=Response,
    summary="Принять события аналитики",
    description=(
        "Сохраняет обезличенные события. Время получения фиксируется "
        "с точностью до часа."
    ),
    response_description="События приняты",
    responses=problem_responses(COMMON_PROBLEMS),
)
async def record_events(session: DbSession, events: EventBatch) -> Response:
    await session.execute(
        insert(AnalyticsEvent).values(
            [
                {
                    "name": event.name,
                    "schema_version": event.schema_version,
                    "app_version": event.app_version,
                    "properties": event.properties.model_dump(),
                }
                for event in events
            ]
        )
    )
    await session.commit()
    return Response(status_code=202)
