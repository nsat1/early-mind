from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


DbSession = Annotated[
    AsyncSession,
    Depends(get_db_session, scope="function"),
]


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


RedisClient = Annotated[Redis, Depends(get_redis)]
