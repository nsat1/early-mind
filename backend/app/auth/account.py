from fastapi import APIRouter
from sqlalchemy import select

from app.auth.dependencies import NOT_AUTHENTICATED, CurrentSession, not_authenticated
from app.auth.models import Account
from app.auth.router import AUTH_PROBLEMS
from app.auth.schemas import AccountOut
from app.core.errors import problem_responses
from app.db.dependencies import DbSession

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get(
    "",
    summary="Данные аккаунта",
    description=(
        "Email аккаунта для экрана родителя. Нужен вход. Каждый запрос продлевает "
        "сессию на 30 дней, но не дальше 90 дней от входа."
    ),
    response_description="Аккаунт",
    responses=problem_responses(
        {
            401: ("Нет действующей сессии, cookie удаляется", NOT_AUTHENTICATED),
            503: AUTH_PROBLEMS[503],
        }
    ),
)
async def get_account(current: CurrentSession, session: DbSession) -> AccountOut:
    email = await session.scalar(
        select(Account.email).where(Account.account_id == current.account_id)
    )
    if email is None:
        raise not_authenticated()
    return AccountOut(email=email)
