from app.core.config import Settings
from app.core.mail import Mail


def app_link(settings: Settings, path: str) -> str:
    return f"{str(settings.app_url).rstrip('/')}/{path}"


def verification_mail(settings: Settings, email: str, token: str) -> Mail:
    link = app_link(settings, f"verify-email#token={token}")
    return Mail(
        to=email,
        subject="Подтвердите email для Early Mind",
        body=(
            "Здравствуйте!\n\n"
            "Вы зарегистрировались в Early Mind. Чтобы подтвердить email, "
            f"откройте ссылку:\n{link}\n\n"
            "Ссылка действует 24 часа. Если вы не регистрировались, "
            "просто удалите это письмо.\n"
        ),
    )


def account_exists_mail(settings: Settings, email: str) -> Mail:
    return Mail(
        to=email,
        subject="Аккаунт Early Mind уже есть",
        body=(
            "Здравствуйте!\n\n"
            "Кто-то, возможно вы, пытался зарегистрироваться в Early Mind "
            "с этим email, но аккаунт уже есть.\n\n"
            f"Войти: {app_link(settings, 'login')}\n"
            "Если не помните пароль, восстановите его на странице входа.\n\n"
            "Если это были не вы, ничего делать не нужно.\n"
        ),
    )
