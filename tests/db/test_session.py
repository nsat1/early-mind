import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.db.session import build_database_url, create_database


def settings(password: str) -> Settings:
    return Settings(
        _env_file=None,
        db_host="db.invalid",
        db_port=5433,
        db_name="sample",
        db_user="app",
        db_password=password,
    )


@pytest.mark.parametrize("password", [" @:/?#% ", "Пароль 🔐", "a'b\"c\\d"])
def test_url_preserves_password(password: str) -> None:
    config = settings(password)
    url = build_database_url(config, config.db_user, config.db_password)
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "app"
    assert (url.host, url.port) == ("db.invalid", 5433)
    assert url.database == "sample"
    assert url.password == password
    assert password not in str(url) + repr(url)


def test_creation_is_lazy(monkeypatch: pytest.MonkeyPatch) -> None:
    connect = AsyncMock(side_effect=AssertionError("Unexpected network connection"))
    monkeypatch.setattr("psycopg.AsyncConnection.connect", connect)
    engine, sessions = create_database(settings("synthetic"))

    async def check() -> None:
        try:
            async with sessions() as first, sessions() as second:
                assert first is not second
        finally:
            await engine.dispose()

    asyncio.run(check())
    connect.assert_not_called()
