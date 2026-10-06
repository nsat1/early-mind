import asyncio
from contextlib import nullcontext
from unittest.mock import AsyncMock, Mock, call

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize("fail", [False, True])
def test_lifespan_closes_and_recreates_resources(
    app: FastAPI, settings: Settings, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    engines = [Mock(dispose=AsyncMock()), Mock(dispose=AsyncMock())]
    factories = [object(), object()]
    create = Mock(side_effect=list(zip(engines, factories, strict=True)))
    monkeypatch.setattr("app.db.lifespan.create_database", create)
    assert not hasattr(app.state, "session_factory")

    async def check() -> None:
        for engine, factory in zip(engines, factories, strict=True):
            expected = (
                pytest.raises(RuntimeError, match="probe") if fail else nullcontext()
            )
            with expected:
                async with app.router.lifespan_context(app):
                    assert app.state.session_factory is factory
                    if fail:
                        raise RuntimeError("probe")
            assert not hasattr(app.state, "session_factory")
            engine.dispose.assert_awaited_once_with()

    asyncio.run(check())
    assert create.call_args_list == [call(settings), call(settings)]


def test_settings_load_only_on_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    load = Mock(side_effect=ValueError("Invalid settings"))
    monkeypatch.setattr("app.db.lifespan.get_settings", load)
    app = create_app()
    load.assert_not_called()
    with pytest.raises(ValueError, match="Invalid settings"), TestClient(app):
        pass
    load.assert_called_once_with()
