from fastapi import FastAPI

from app.alphabet.router import router as alphabet_router
from app.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Early Mind")
    app.include_router(health_router)
    app.include_router(alphabet_router)
    return app
