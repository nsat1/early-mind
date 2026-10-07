import os
import secrets
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import MigrationSettings, Settings


@pytest.fixture(autouse=True)
def clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if name.upper().startswith("DB_"):
            monkeypatch.delenv(name)


def test_file_and_priorities(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    password = f" Пароль 🔐 {secrets.token_urlsafe(16)} "
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"POSTGRES_PASSWORD=ignored\nDB_PASSWORD='{password}'\n"
        "DB_HOST=' db '\nDB_NAME=' early_mind '\n"
        "DB_USER=' early_mind_app '\nDB_PORT=5433\n",
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
    monkeypatch.setenv("DB_PORT", "5434")
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


def test_roles_do_not_share_credentials() -> None:
    assert "db_migration_password" not in Settings.model_fields
    assert "db_password" not in MigrationSettings.model_fields
    password = secrets.token_urlsafe(16)
    assert Settings(_env_file=None, db_password=password).db_user == "early_mind_app"
    migration = MigrationSettings(_env_file=None, db_migration_password=password)
    assert migration.db_migration_user == "early_mind_migrator"


def test_migration_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    password = f" Пароль 🔐 {secrets.token_urlsafe(16)} "
    environment = {
        "DB_HOST": "db",
        "DB_PORT": "5433",
        "DB_NAME": "sample",
        "DB_MIGRATION_USER": "migrator",
        "DB_MIGRATION_PASSWORD": password,
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    settings = MigrationSettings(_env_file=None)
    assert settings.db_host == "db"
    assert settings.db_port == 5433
    assert settings.db_name == "sample"
    assert settings.db_migration_user == "migrator"
    assert settings.db_migration_password.get_secret_value() == password
    assert password not in str(settings) + repr(settings) + settings.model_dump_json()


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"db_migration_password": ""},
        {"db_migration_user": " ", "db_migration_password": "hidden-input"},
    ],
)
def test_invalid_migration_settings(values: dict[str, str]) -> None:
    with pytest.raises(ValidationError) as error:
        MigrationSettings(_env_file=None, **values)
    assert "input_value" not in str(error.value)
    assert "hidden-input" not in str(error.value)
