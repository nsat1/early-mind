from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.db.redis import create_redis
from app.db.session import create_database


@asynccontextmanager
async def lifespan(
    app: FastAPI, *, settings: Settings | None = None
) -> AsyncIterator[None]:
    settings = settings if settings is not None else get_settings()
    engine, factory = create_database(settings)
    redis = create_redis(settings)
    app.state.session_factory = factory
    app.state.redis = redis
    try:
        yield
    finally:
        del app.state.session_factory, app.state.redis
        await redis.aclose()
        await engine.dispose()
