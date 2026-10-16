from app.core.config import Settings
from app.db.session import build_database_url


def test_url_preserves_password() -> None:
    special_characters = " @:/?#% Пароль 🔐 a'b\"c\\d"
    config = Settings(
        _env_file=None,
        db_host="db.invalid",
        db_port=5433,
        db_name="sample",
        db_user="app",
        db_password=special_characters,
        redis_password=special_characters,
    )

    url = build_database_url(config, config.db_user, config.db_password)

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "app"
    assert (url.host, url.port) == ("db.invalid", 5433)
    assert url.database == "sample"
    assert url.password == special_characters
    assert special_characters not in str(url) + repr(url)
