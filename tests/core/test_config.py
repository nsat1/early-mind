import os
import secrets
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if name.upper().startswith("EARLY_MIND_"):
            monkeypatch.delenv(name)


def test_file_and_priorities(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    password = f" Пароль 🔐 {secrets.token_urlsafe(16)} "
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"POSTGRES_PASSWORD=ignored\nEARLY_MIND_DB_PASSWORD='{password}'\n"
        "EARLY_MIND_DB_HOST=' db '\nEARLY_MIND_DB_NAME=' early_mind '\n"
        "EARLY_MIND_DB_USER=' early_mind_app '\nEARLY_MIND_DB_PORT=5433\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    settings = Settings(_env_file=env_file)
    assert settings.db_host == "db"
    assert settings.db_port == 5433
    assert settings.db_name == "early_mind"
    assert settings.db_user == "early_mind_app"
    assert settings.db_password.get_secret_value() == password
    assert password not in str(settings) + repr(settings) + settings.model_dump_json()
    monkeypatch.setenv("EARLY_MIND_DB_PORT", "5434")
    assert Settings(_env_file=env_file).db_port == 5434
    assert Settings(_env_file=env_file, db_port=5435).db_port == 5435


@pytest.mark.parametrize(
    "values",
    [{}, {"db_password": ""}]
    + [{"db_port": value} for value in (0, 65536, "hidden-input")]
    + [{field: " "} for field in ("db_host", "db_name", "db_user")],
)
def test_invalid_settings(values: dict[str, object]) -> None:
    if values and "db_password" not in values:
        values = {**values, "db_password": secrets.token_urlsafe(16)}
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **values)
    assert "input_value" not in str(error.value)
    assert "hidden-input" not in str(error.value)
