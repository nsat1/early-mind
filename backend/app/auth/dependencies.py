from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyCookie

from app.auth.sessions import (
    SESSION_COOKIE,
    Session,
    expired_session_cookie,
    read_session,
)
from app.db.dependencies import RedisClient

NOT_AUTHENTICATED = "Not authenticated"

session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    scheme_name="session",
    description="Cookie сессии: ставится при входе, браузер отправляет её сам",
    auto_error=False,
)


def not_authenticated() -> HTTPException:
    return HTTPException(
        401, NOT_AUTHENTICATED, headers={"Set-Cookie": expired_session_cookie()}
    )


async def current_session(
    redis: RedisClient, session_id: Annotated[str | None, Depends(session_cookie)]
) -> Session:
    session = None if session_id is None else await read_session(redis, session_id)
    if session is None:
        raise not_authenticated()
    return session


CurrentSession = Annotated[Session, Depends(current_session)]
