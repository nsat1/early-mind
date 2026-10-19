import hashlib
import hmac
import uuid
from datetime import timedelta

from pydantic import SecretStr
from redis.asyncio import Redis

MAILS_PER_ACCOUNT = 3
MAIL_LIMIT_WINDOW = timedelta(hours=1)
MAX_ATTEMPTS = 5
ATTEMPTS_PAUSE = timedelta(minutes=15)
IP_REQUESTS_LIMIT = 30


def mail_counter_key(account_id: uuid.UUID) -> str:
    return f"emails:{account_id}"


async def allow_mail(redis: Redis, account_id: uuid.UUID) -> bool:
    key = mail_counter_key(account_id)
    async with redis.pipeline() as pipeline:
        count, _ = (
            await pipeline.incr(key).expire(key, MAIL_LIMIT_WINDOW, nx=True).execute()
        )
    return count <= MAILS_PER_ACCOUNT


def keyed_digest(secret: SecretStr, value: str) -> str:
    return hmac.new(
        secret.get_secret_value().encode(), value.encode(), hashlib.sha256
    ).hexdigest()


def login_failures_key(secret: SecretStr, email: str) -> str:
    return f"login-failures:{keyed_digest(secret, email)}"


def ip_requests_key(secret: SecretStr, host: str) -> str:
    return f"rate:{keyed_digest(secret, host)}"


def password_failures_key(account_id: uuid.UUID) -> str:
    return f"password-failures:{account_id}"


async def count_attempt(redis: Redis, key: str) -> int:
    async with redis.pipeline() as pipeline:
        attempt, _ = (
            await pipeline.incr(key).expire(key, ATTEMPTS_PAUSE, nx=True).execute()
        )
    return attempt


async def pause_attempts(redis: Redis, key: str) -> None:
    await redis.expire(key, ATTEMPTS_PAUSE)


async def attempts_retry_after(redis: Redis, key: str) -> int:
    return max(await redis.ttl(key), 1)


async def clear_account_limits(
    redis: Redis, secret: SecretStr, account_id: uuid.UUID, email: str
) -> None:
    await redis.delete(
        mail_counter_key(account_id),
        password_failures_key(account_id),
        login_failures_key(secret, email),
    )
