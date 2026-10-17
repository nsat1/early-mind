import secrets
import time
import uuid
from datetime import timedelta

from fastapi import Response
from redis.asyncio import Redis

from app.auth.tokens import token_hash

SESSION_COOKIE = "__Host-session"
SESSION_IDLE_TTL = timedelta(days=30)
SESSION_MAX_AGE = timedelta(days=90)


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
