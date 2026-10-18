from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie
from pydantic import HttpUrl

from app.auth.sessions import (
    SESSION_COOKIE,
    Session,
    expired_session_cookie,
    read_session,
)
from app.db.dependencies import AppSettings, RedisClient

NOT_AUTHENTICATED = "Not authenticated"
ORIGIN_NOT_ALLOWED = "Request origin not allowed"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
DEFAULT_PORTS = {"http": 80, "https": 443}

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


def app_origin(app_url: HttpUrl) -> str:
    origin = f"{app_url.scheme}://{app_url.host}"
    if app_url.port != DEFAULT_PORTS.get(app_url.scheme):
        origin += f":{app_url.port}"
    return origin


async def check_origin(request: Request, settings: AppSettings) -> None:
    if request.method not in UNSAFE_METHODS:
        return
    if request.headers.get("origin") != app_origin(settings.app_url):
        raise HTTPException(403, ORIGIN_NOT_ALLOWED)
