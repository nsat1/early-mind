import pytest
from redis.asyncio import Redis

from app.core.config import Settings
from app.db.redis import create_redis


def test_redis_client_fails_fast(settings: Settings) -> None:
    options = create_redis(settings).connection_pool.connection_kwargs

    assert options["retry"] is None
    assert options["socket_connect_timeout"] == options["socket_timeout"] == 2
    assert options["decode_responses"] is True


@pytest.mark.integration
@pytest.mark.anyio
async def test_redis_stores_value_with_expiry(redis_client: Redis) -> None:
    await redis_client.set("probe", "значение", ex=60)

    assert await redis_client.get("probe") == "значение"
    assert 0 < await redis_client.ttl("probe") <= 60
