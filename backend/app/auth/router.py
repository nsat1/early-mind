from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.auth.dependencies import NOT_AUTHENTICATED, CurrentSession, session_cookie
from app.auth.limits import (
    LOGIN_ATTEMPTS,
    allow_mail,
    count_login_attempt,
    login_failures_key,
    login_retry_after,
    pause_login,
)
from app.auth.mails import account_exists_mail, verification_mail
from app.auth.models import Account, Consent
from app.auth.passwords import (
    PasswordError,
    check_password,
    hash_password,
    verify_account_password,
)
from app.auth.schemas import (
    EmailVerification,
    Login,
    Registration,
    VerificationResend,
)
from app.auth.sessions import (
    create_session,
    end_account_sessions,
    end_session,
    expired_session_cookie,
    set_session_cookie,
)
from app.auth.tokens import consume_email_token, store_email_token
from app.core.errors import (
    COMMON_PROBLEMS,
    DATABASE_UNAVAILABLE,
    INVALID_PARAMETERS,
    problem_responses,
)
from app.core.mail import send_mail
from app.db.dependencies import AppSettings, DbSession, RedisClient

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

INVALID_LINK = "Invalid or expired link"
INVALID_CREDENTIALS = "Invalid email or password"
EMAIL_NOT_VERIFIED = "Email not verified"
TOO_MANY_LOGIN_ATTEMPTS = "Too many login attempts"
AUTH_PROBLEMS = {
    422: COMMON_PROBLEMS[422],
    503: ("База данных или хранилище сессий недоступны", DATABASE_UNAVAILABLE),
}
LOGIN_PROBLEMS = problem_responses(
    {
        401: ("Неверный email или пароль", INVALID_CREDENTIALS),
        403: ("Пароль верный, но email не подтверждён", EMAIL_NOT_VERIFIED),
        429: (
            "Вход приостановлен после 5 неудачных попыток за 15 минут",
            TOO_MANY_LOGIN_ATTEMPTS,
        ),
    }
    | AUTH_PROBLEMS
)
LOGIN_PROBLEMS[429]["headers"] = {
    "Retry-After": {
        "description": "Через сколько секунд можно повторить вход",
        "schema": {"type": "integer"},
    }
}


def password_problem(error: PasswordError) -> RequestValidationError:
    return RequestValidationError(
        [{"type": error.code, "loc": ("body", "password"), "msg": str(error)}]
    )


@router.post(
    "/register",
    status_code=202,
    response_class=Response,
    summary="Зарегистрировать аккаунт родителя",
    description=(
        "Создаёт неподтверждённый аккаунт и отправляет письмо со ссылкой "
        "подтверждения. Если email уже зарегистрирован, ответ тот же, а письмо "
        "сообщает, что аккаунт уже есть: по ответу нельзя узнать, "
        "зарегистрирован ли email."
    ),
    response_description="Запрос принят, письмо будет отправлено",
    responses=problem_responses(
        AUTH_PROBLEMS
        | {
            422: (
                "Параметры запроса не прошли проверку или пароль не по правилам",
                INVALID_PARAMETERS,
            )
        }
    ),
)
async def register(
    registration: Registration,
    session: DbSession,
    redis: RedisClient,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
) -> Response:
    try:
        check_password(registration.password, registration.email)
    except PasswordError as error:
        raise password_problem(error) from error
    password_hash = await run_in_threadpool(hash_password, registration.password)
    account_id = await session.scalar(
        insert(Account)
        .values(email=registration.email, password_hash=password_hash)
        .on_conflict_do_nothing(index_elements=[Account.email])
        .returning(Account.account_id)
    )
    if account_id is None:
        account_id = await session.scalar(
            select(Account.account_id).where(Account.email == registration.email)
        )
        mail = account_exists_mail(settings, registration.email)
    else:
        await session.execute(
            insert(Consent).values(
                account_id=account_id, policy_version=registration.policy_version
            )
        )
        token = await store_email_token(redis, account_id)
        mail = verification_mail(settings, registration.email, token)
    if account_id is not None and await allow_mail(redis, account_id):
        background_tasks.add_task(send_mail, settings, mail)
    await session.commit()
    return Response(status_code=202)


@router.post(
    "/email-verification",
    status_code=204,
    response_class=Response,
    summary="Подтвердить email",
    description=(
        "Подтверждает email по токену из ссылки в письме. Ссылка действует "
        "24 часа и только один раз."
    ),
    response_description="Email подтверждён",
    responses=problem_responses(
        {
            400: (
                "Ссылка устарела, уже использована или аккаунт удалён",
                INVALID_LINK,
            )
        }
        | AUTH_PROBLEMS
    ),
)
async def verify_email(
    verification: EmailVerification, session: DbSession, redis: RedisClient
) -> Response:
    account_id = await consume_email_token(redis, verification.token)
    if account_id is not None:
        account_id = await session.scalar(
            update(Account)
            .where(Account.account_id == account_id)
            .values(
                email_verified_at=func.coalesce(Account.email_verified_at, func.now())
            )
            .returning(Account.account_id)
        )
    if account_id is None:
        raise HTTPException(400, INVALID_LINK)
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/email-verification/resend",
    status_code=202,
    response_class=Response,
    summary="Отправить письмо подтверждения ещё раз",
    description=(
        "Если аккаунт есть и email не подтверждён, отправляет письмо с новой "
        "ссылкой, прежняя перестаёт работать. Не больше 3 писем в час на аккаунт. "
        "Ответ одинаковый в любом случае."
    ),
    response_description="Запрос принят",
    responses=problem_responses(AUTH_PROBLEMS),
)
async def resend_verification(
    resend: VerificationResend,
    session: DbSession,
    redis: RedisClient,
    settings: AppSettings,
    background_tasks: BackgroundTasks,
) -> Response:
    account_id = await session.scalar(
        select(Account.account_id).where(
            Account.email == resend.email, Account.email_verified_at.is_(None)
        )
    )
    if account_id is not None and await allow_mail(redis, account_id):
        token = await store_email_token(redis, account_id)
        background_tasks.add_task(
            send_mail, settings, verification_mail(settings, resend.email, token)
        )
    return Response(status_code=202)


@router.post(
    "/login",
    status_code=204,
    response_class=Response,
    summary="Войти",
    description=(
        "Проверяет email и пароль и ставит cookie сессии. Каждый вход создаёт "
        "новую сессию. О неподтверждённом email ответ сообщает только после "
        "верного пароля."
    ),
    response_description="Вход выполнен",
    responses={
        204: {
            "headers": {
                "Set-Cookie": {
                    "description": (
                        "`__Host-session=<идентификатор>; HttpOnly; Secure; "
                        "SameSite=Lax; Path=/; Max-Age=7776000`"
                    ),
                    "schema": {"type": "string"},
                }
            }
        }
    }
    | LOGIN_PROBLEMS,
)
async def login(
    credentials: Login, session: DbSession, redis: RedisClient, settings: AppSettings
) -> Response:
    failures_key = login_failures_key(settings.auth_secret, credentials.email)
    attempt = await count_login_attempt(redis, failures_key)
    if attempt > LOGIN_ATTEMPTS:
        retry_after = await login_retry_after(redis, failures_key)
        raise HTTPException(
            429, TOO_MANY_LOGIN_ATTEMPTS, headers={"Retry-After": str(retry_after)}
        )
    account = (
        await session.execute(
            select(
                Account.account_id, Account.password_hash, Account.email_verified_at
            ).where(Account.email == credentials.email)
        )
    ).one_or_none()
    valid = await run_in_threadpool(
        verify_account_password,
        credentials.password,
        None if account is None else account.password_hash,
    )
    if account is None or not valid:
        if attempt == LOGIN_ATTEMPTS:
            await pause_login(redis, failures_key)
        raise HTTPException(401, INVALID_CREDENTIALS)
    await redis.delete(failures_key)
    if account.email_verified_at is None:
        raise HTTPException(403, EMAIL_NOT_VERIFIED)
    response = Response(status_code=204)
    set_session_cookie(response, await create_session(redis, account.account_id))
    return response


def logged_out() -> Response:
    return Response(status_code=204, headers={"Set-Cookie": expired_session_cookie()})


@router.post(
    "/logout",
    status_code=204,
    response_class=Response,
    summary="Выйти",
    description=(
        "Завершает текущую сессию и удаляет cookie. Если сессии уже нет, ответ тот же."
    ),
    response_description="Сессия завершена",
    responses=problem_responses({503: AUTH_PROBLEMS[503]}),
)
async def logout(
    redis: RedisClient, session_id: Annotated[str | None, Depends(session_cookie)]
) -> Response:
    if session_id is not None:
        await end_session(redis, session_id)
    return logged_out()


@router.post(
    "/logout-all",
    status_code=204,
    response_class=Response,
    summary="Выйти на всех устройствах",
    description="Завершает все сессии аккаунта, включая текущую, и удаляет cookie.",
    response_description="Все сессии завершены",
    responses=problem_responses(
        {401: ("Нет действующей сессии", NOT_AUTHENTICATED), 503: AUTH_PROBLEMS[503]}
    ),
)
async def logout_all(current: CurrentSession, redis: RedisClient) -> Response:
    await end_account_sessions(redis, current.account_id)
    return logged_out()
