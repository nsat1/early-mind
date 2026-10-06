from functools import partial

from fastapi import FastAPI

from app.alphabet.router import router as alphabet_router
from app.core.config import Settings
from app.db.lifespan import lifespan
from app.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="Early Mind", lifespan=partial(lifespan, settings=settings))
    app.include_router(health_router)
    app.include_router(alphabet_router)
    return app
