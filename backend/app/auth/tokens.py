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
    await redis.set(email_token_key(token), str(account_id), ex=EMAIL_TOKEN_TTL)
    return token


async def consume_email_token(redis: Redis, token: str) -> uuid.UUID | None:
    account_id = await redis.getdel(email_token_key(token))
    return None if account_id is None else uuid.UUID(account_id)
