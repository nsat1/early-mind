import hashlib
import secrets
import uuid
from datetime import timedelta

from redis.asyncio import Redis

EMAIL_TOKEN_TTL = timedelta(hours=24)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def email_token_key(token: str) -> str:
    return f"email-token:{token_hash(token)}"


async def store_email_token(redis: Redis, account_id: uuid.UUID) -> str:
    token = secrets.token_urlsafe(32)
    key = email_token_key(token)
    previous = await redis.set(
        f"account-email-token:{account_id}", key, ex=EMAIL_TOKEN_TTL, get=True
    )
    async with redis.pipeline() as pipeline:
        if previous is not None:
            pipeline.delete(previous)
        await pipeline.set(key, str(account_id), ex=EMAIL_TOKEN_TTL).execute()
    return token


async def consume_email_token(redis: Redis, token: str) -> uuid.UUID | None:
    account_id = await redis.getdel(email_token_key(token))
    return None if account_id is None else uuid.UUID(account_id)
