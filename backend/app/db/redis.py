from redis.asyncio import Redis

from app.core.config import Settings

REDIS_TIMEOUT_SECONDS = 2


def create_redis(settings: Settings) -> Redis:
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value(),
        decode_responses=True,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        retry=None,
    )
