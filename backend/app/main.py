from functools import partial
from operator import attrgetter
from pathlib import Path

from fastapi import FastAPI

from app.alphabet.media import MEDIA_URL, MediaFiles
from app.alphabet.router import router as alphabet_router
from app.alphabet.source import CONTENT_DIR
from app.analytics.router import router as analytics_router
from app.auth.router import router as auth_router
from app.core.config import Settings
from app.core.errors import register_problem_details
from app.db.lifespan import lifespan
from app.health import router as health_router

OPENAPI_TAGS = [
    {"name": "alphabet", "description": "Азбука: буквы алфавита и слова-примеры"},
    {"name": "analytics", "description": "Обезличенные события аналитики"},
    {"name": "auth", "description": "Аккаунт родителя: регистрация и вход"},
    {"name": "health", "description": "Проверки работоспособности для мониторинга"},
]


def create_app(
    settings: Settings | None = None, content_dir: Path = CONTENT_DIR
) -> FastAPI:
    app = FastAPI(
        title="Early Mind API",
        summary="API платформы обучения Early Mind",
        description=(
            "Ошибки возвращаются в формате Problem Details (RFC 9457) с типом "
            "`application/problem+json`."
        ),
        openapi_tags=OPENAPI_TAGS,
        generate_unique_id_function=attrgetter("name"),
        lifespan=partial(lifespan, settings=settings),
    )
    register_problem_details(app)
    app.include_router(health_router)
    app.include_router(alphabet_router)
    app.include_router(analytics_router)
    app.include_router(auth_router)
    app.mount(
        MEDIA_URL, MediaFiles(directory=content_dir, check_dir=False), name="media"
    )
    return app
