import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_lifespan_opens_and_closes_resources(
    app: FastAPI, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, factory, redis = (
        Mock(dispose=AsyncMock()),
        object(),
        Mock(aclose=AsyncMock()),
    )
    create_database = Mock(return_value=(engine, factory))
    create_redis = Mock(return_value=redis)
    monkeypatch.setattr("app.db.lifespan.create_database", create_database)
    monkeypatch.setattr("app.db.lifespan.create_redis", create_redis)

    async def check() -> None:
        async with app.router.lifespan_context(app):
            assert app.state.session_factory is factory
            assert app.state.redis is redis
        assert not hasattr(app.state, "session_factory")
        assert not hasattr(app.state, "redis")

    asyncio.run(check())
    create_database.assert_called_once_with(settings)
    create_redis.assert_called_once_with(settings)
    engine.dispose.assert_awaited_once_with()
    redis.aclose.assert_awaited_once_with()


def test_settings_load_only_on_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    load = Mock(side_effect=ValueError("Invalid settings"))
    monkeypatch.setattr("app.db.lifespan.get_settings", load)
    app = create_app()
    load.assert_not_called()
    with pytest.raises(ValueError, match="Invalid settings"), TestClient(app):
        pass
    load.assert_called_once_with()
