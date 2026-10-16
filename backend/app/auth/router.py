from fastapi import APIRouter, BackgroundTasks, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from sqlalchemy.dialects.postgresql import insert

from app.auth.mails import account_exists_mail, verification_mail
from app.auth.models import Account, Consent
from app.auth.passwords import PasswordError, check_password, hash_password
from app.auth.schemas import Registration
from app.auth.tokens import store_email_token
from app.core.errors import DATABASE_UNAVAILABLE, INVALID_PARAMETERS, problem_responses
from app.core.mail import send_mail
from app.db.dependencies import AppSettings, DbSession, RedisClient

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

AUTH_PROBLEMS = {
    422: (
        "Параметры запроса не прошли проверку или пароль не по правилам",
        INVALID_PARAMETERS,
    ),
    503: ("База данных или хранилище сессий недоступны", DATABASE_UNAVAILABLE),
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
    responses=problem_responses(AUTH_PROBLEMS),
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
        mail = account_exists_mail(settings, registration.email)
    else:
        await session.execute(
            insert(Consent).values(
                account_id=account_id, policy_version=registration.policy_version
            )
        )
        token = await store_email_token(redis, account_id)
        await session.commit()
        mail = verification_mail(settings, registration.email, token)
    background_tasks.add_task(send_mail, settings, mail)
    return Response(status_code=202)
