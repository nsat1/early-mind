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
            "с этим email, но аккаунт уже создан.\n\n"
            f"Войти: {app_link(settings, 'login')}\n"
            "Если не помните пароль, восстановите его на странице входа.\n\n"
            "Если это были не вы, ничего делать не нужно.\n"
        ),
    )


def reset_mail(settings: Settings, email: str, token: str) -> Mail:
    link = app_link(settings, f"reset-password#token={token}")
    return Mail(
        to=email,
        subject="Восстановление пароля Early Mind",
        body=(
            "Здравствуйте!\n\n"
            "Восстановление пароля в Early Mind. "
            f"Чтобы задать новый пароль, откройте ссылку:\n{link}\n\n"
            "Ссылка действует 1 час. Если вы не запрашивали восстановление, "
            "ничего делать не нужно — пароль останется прежним.\n"
        ),
    )
