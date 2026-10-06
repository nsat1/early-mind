from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.db.session import create_database


@asynccontextmanager
async def lifespan(
    app: FastAPI, *, settings: Settings | None = None
) -> AsyncIterator[None]:
    engine, factory = create_database(
        settings if settings is not None else get_settings()
    )
    app.state.session_factory = factory
    try:
        yield
    finally:
        del app.state.session_factory
        await engine.dispose()
