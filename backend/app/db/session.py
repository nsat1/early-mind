from pydantic import SecretStr
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseSettings, Settings


def build_database_url(
    settings: DatabaseSettings, user: str, password: SecretStr
) -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=user,
        password=password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )


def create_database(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        build_database_url(settings, settings.db_user, settings.db_password),
        pool_size=5,
        max_overflow=0,
        pool_timeout=10,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
        hide_parameters=True,
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)
