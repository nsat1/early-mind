import hashlib
import hmac
import uuid
from datetime import timedelta

from pydantic import SecretStr
from redis.asyncio import Redis

MAILS_PER_ACCOUNT = 3
MAIL_LIMIT_WINDOW = timedelta(hours=1)
LOGIN_ATTEMPTS = 5
LOGIN_PAUSE = timedelta(minutes=15)


async def allow_mail(redis: Redis, account_id: uuid.UUID) -> bool:
    key = f"emails:{account_id}"
    async with redis.pipeline() as pipeline:
        count, _ = (
            await pipeline.incr(key).expire(key, MAIL_LIMIT_WINDOW, nx=True).execute()
        )
    return count <= MAILS_PER_ACCOUNT


def login_failures_key(secret: SecretStr, email: str) -> str:
    digest = hmac.new(
        secret.get_secret_value().encode(), email.encode(), hashlib.sha256
    ).hexdigest()
    return f"login-failures:{digest}"


async def count_login_attempt(redis: Redis, key: str) -> int:
    async with redis.pipeline() as pipeline:
        attempt, _ = (
            await pipeline.incr(key).expire(key, LOGIN_PAUSE, nx=True).execute()
        )
    return attempt


async def pause_login(redis: Redis, key: str) -> None:
    await redis.expire(key, LOGIN_PAUSE)


async def login_retry_after(redis: Redis, key: str) -> int:
    return max(await redis.ttl(key), 1)
