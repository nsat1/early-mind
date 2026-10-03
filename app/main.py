from fastapi import FastAPI

from app.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Early Mind")
    app.include_router(health_router)
    return app
