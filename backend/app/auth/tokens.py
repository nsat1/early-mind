import hashlib
import secrets
import uuid
from datetime import timedelta

from redis.asyncio import Redis

EMAIL_TOKEN_TTL = timedelta(hours=24)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_email_token(redis: Redis, account_id: uuid.UUID) -> str:
    token = secrets.token_urlsafe(32)
    await redis.set(
        f"email-token:{token_hash(token)}", str(account_id), ex=EMAIL_TOKEN_TTL
    )
    return token
