import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from redis.asyncio import Redis
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    NOT_AUTHENTICATED,
    CurrentSession,
    check_origin,
    not_authenticated,
)
from app.auth.limits import (
    MAX_ATTEMPTS,
    attempts_retry_after,
    clear_account_limits,
    count_attempt,
    password_failures_key,
    pause_attempts,
)
from app.auth.mails import password_changed_mail
from app.auth.models import Account
from app.auth.passwords import (
    PasswordError,
    check_password,
    hash_password,
    verify_password,
)
from app.auth.router import (
    AUTH_PROBLEMS,
    PASSWORD_PROBLEMS,
    RETRY_AFTER_HEADER,
    logged_out,
    password_problem,
)
from app.auth.schemas import AccountDeletion, AccountOut, PasswordChange
from app.auth.sessions import end_account_sessions
from app.auth.tokens import revoke_tokens
from app.core.errors import problem_responses
from app.core.mail import send_mail
from app.db.dependencies import AppSettings, DbSession, RedisClient

router = APIRouter(
    prefix="/api/v1/account", tags=["account"], dependencies=[Depends(check_origin)]
)

CONFIRMATION_REJECTED = "Incorrect password"
CONFIRMATION_PAUSED = "Too many password attempts"
SESSION_PROBLEMS = {
    401: ("Нет действующей сессии, cookie удаляется", NOT_AUTHENTICATED),
    503: AUTH_PROBLEMS[503],
}


def confirmation_responses(
    problems: dict[int, tuple[str, str]],
) -> dict[int | str, dict[str, Any]]:
    merged = (
        {
            403: (
                "Пароль неверный или запрос пришёл с чужого сайта",
                CONFIRMATION_REJECTED,
            ),
            429: (
                "Пароль неверный 5 раз за 15 минут, проверка приостановлена",
                CONFIRMATION_PAUSED,
            ),
        }
        | SESSION_PROBLEMS
        | problems
    )
    responses = problem_responses(dict(sorted(merged.items())))
    responses[429]["headers"] = RETRY_AFTER_HEADER
    return responses


async def confirm_password(
    redis: Redis, session: AsyncSession, account_id: uuid.UUID, password: str
) -> str:
    failures_key = password_failures_key(account_id)
    attempt = await count_attempt(redis, failures_key)
    if attempt > MAX_ATTEMPTS:
        retry_after = await attempts_retry_after(redis, failures_key)
        raise HTTPException(
            429, CONFIRMATION_PAUSED, headers={"Retry-After": str(retry_after)}
        )
    account = (
        await session.execute(
            select(Account.email, Account.password_hash).where(
                Account.account_id == account_id
            )
        )
    ).one_or_none()
    if account is None:
        raise not_authenticated()
    if not await run_in_threadpool(verify_password, password, account.password_hash):
        if attempt == MAX_ATTEMPTS:
            await pause_attempts(redis, failures_key)
        raise HTTPException(403, CONFIRMATION_REJECTED)
    await redis.delete(failures_key)
    return account.email


@router.get(
    "",
    summary="Данные аккаунта",
    description=(
        "Email аккаунта для экрана родителя. Нужен вход. Каждый запрос продлевает "
        "сессию на 30 дней, но не дальше 90 дней от входа."
    ),
    response_description="Аккаунт",
    responses=problem_responses(SESSION_PROBLEMS),
)
async def get_account(current: CurrentSession, session: DbSession) -> AccountOut:
    email = await session.scalar(
        select(Account.email).where(Account.account_id == current.account_id)
    )
    if email is None:
        raise not_authenticated()
    return AccountOut(email=email)


@router.put(
    "/password",
    status_code=204,
    response_class=Response,
    summary="Сменить пароль",
    description=(
        "Меняет пароль после проверки текущего и завершает остальные сессии "
        "аккаунта, текущая продолжает работать. После 5 неверных текущих паролей "
        "за 15 минут проверка приостанавливается. На email приходит письмо "
        "о смене пароля."
    ),
    response_description="Пароль изменён",
    responses=confirmation_responses(PASSWORD_PROBLEMS),
)
async def change_password(
    change: PasswordChange,
    current: CurrentSession,
    session: DbSession,
    redis: RedisClient,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
) -> Response:
    email = await confirm_password(
        redis, session, current.account_id, change.current_password
    )
    try:
        check_password(change.password, email)
    except PasswordError as error:
        raise password_problem(error) from error
    password_hash = await run_in_threadpool(hash_password, change.password)
    await session.execute(
        update(Account)
        .where(Account.account_id == current.account_id)
        .values(password_hash=password_hash)
    )
    await end_account_sessions(redis, current.account_id, keep=current.session_hash)
    await session.commit()
    background_tasks.add_task(
        send_mail, settings, password_changed_mail(settings, email)
    )
    return Response(status_code=204)


@router.post(
    "/deletion",
    status_code=204,
    response_class=Response,
    summary="Удалить аккаунт",
    description=(
        "Безвозвратно удаляет аккаунт после проверки пароля: согласия, все "
        "сессии, ссылки из писем и счётчики попыток. Лимит неверных паролей "
        "общий со сменой пароля."
    ),
    response_description="Аккаунт удалён",
    responses=confirmation_responses(AUTH_PROBLEMS),
)
async def delete_account(
    deletion: AccountDeletion,
    current: CurrentSession,
    session: DbSession,
    redis: RedisClient,
    settings: AppSettings,
) -> Response:
    email = await confirm_password(
        redis, session, current.account_id, deletion.password
    )
    await session.execute(
        delete(Account).where(Account.account_id == current.account_id)
    )
    await end_account_sessions(redis, current.account_id)
    await revoke_tokens(redis, current.account_id)
    await clear_account_limits(redis, settings.auth_secret, current.account_id, email)
    await session.commit()
    return logged_out()
