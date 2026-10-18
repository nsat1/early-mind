import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Response
from redis.asyncio import Redis

from app.auth.tokens import token_hash

SESSION_COOKIE = "__Host-session"
SESSION_IDLE_TTL = timedelta(days=30)
SESSION_MAX_AGE = timedelta(days=90)


@dataclass(frozen=True, slots=True)
class Session:
    account_id: uuid.UUID
    session_hash: str


async def create_session(redis: Redis, account_id: uuid.UUID) -> str:
    session_id = secrets.token_urlsafe(32)
    session_hash = token_hash(session_id)
    session_key = f"session:{session_hash}"
    sessions_key = f"account-sessions:{account_id}"
    async with redis.pipeline() as pipeline:
        await (
            pipeline.hset(
                session_key,
                mapping={"account_id": str(account_id), "created_at": int(time.time())},
            )
            .expire(session_key, SESSION_IDLE_TTL)
            .sadd(sessions_key, session_hash)
            .expire(sessions_key, SESSION_MAX_AGE)
            .execute()
        )
    return session_id


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=int(SESSION_MAX_AGE.total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


async def read_session(redis: Redis, session_id: str) -> Session | None:
    session_hash = token_hash(session_id)
    session_key = f"session:{session_hash}"
    stored = await redis.hgetall(session_key)
    if not stored:
        return None
    ends_at = int(stored["created_at"]) + int(SESSION_MAX_AGE.total_seconds())
    remaining = ends_at - int(time.time())
    if remaining <= 0:
        await redis.delete(session_key)
        return None
    await redis.expire(
        session_key, min(int(SESSION_IDLE_TTL.total_seconds()), remaining)
    )
    return Session(uuid.UUID(stored["account_id"]), session_hash)


def expired_session_cookie() -> str:
    response = Response()
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax"
    )
    return response.headers["set-cookie"]
