import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from redis.asyncio import Redis


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class TokenKind:
    prefix: str
    ttl: timedelta

    def key(self, token: str) -> str:
        return f"{self.prefix}:{token_hash(token)}"


EMAIL_TOKEN = TokenKind("email-token", timedelta(hours=24))
RESET_TOKEN = TokenKind("reset-token", timedelta(hours=1))


async def store_token(redis: Redis, kind: TokenKind, account_id: uuid.UUID) -> str:
    token = secrets.token_urlsafe(32)
    key = kind.key(token)
    previous = await redis.set(
        f"account-{kind.prefix}:{account_id}", key, ex=kind.ttl, get=True
    )
    async with redis.pipeline() as pipeline:
        if previous is not None:
            pipeline.delete(previous)
        await pipeline.set(key, str(account_id), ex=kind.ttl).execute()
    return token


async def find_token(redis: Redis, kind: TokenKind, token: str) -> uuid.UUID | None:
    account_id = await redis.get(kind.key(token))
    return None if account_id is None else uuid.UUID(account_id)


async def consume_token(redis: Redis, kind: TokenKind, token: str) -> uuid.UUID | None:
    account_id = await redis.getdel(kind.key(token))
    return None if account_id is None else uuid.UUID(account_id)
