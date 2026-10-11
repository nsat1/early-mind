from functools import partial
from operator import attrgetter

from fastapi import FastAPI

from app.alphabet.router import router as alphabet_router
from app.core.config import Settings
from app.core.errors import register_problem_details
from app.db.lifespan import lifespan
from app.health import router as health_router

OPENAPI_TAGS = [
    {"name": "alphabet", "description": "Азбука: буквы алфавита и слова-примеры"},
    {"name": "health", "description": "Проверки работоспособности для мониторинга"},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Early Mind API",
        summary="API платформы раннего обучения Early Mind",
        description=(
            "Контент азбуки для веб-приложения. Ошибки возвращаются в формате "
            "Problem Details (RFC 9457) с типом `application/problem+json`."
        ),
        openapi_tags=OPENAPI_TAGS,
        generate_unique_id_function=attrgetter("name"),
        lifespan=partial(lifespan, settings=settings),
    )
    register_problem_details(app)
    app.include_router(health_router)
    app.include_router(alphabet_router)
    return app
