import psycopg
import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.integration


def test_migrations_downgrade_completely(
    alembic_config: Config, migrator_connection: psycopg.Connection
) -> None:
    command.downgrade(alembic_config, "base")
    tables = migrator_connection.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ).fetchall()
    command.upgrade(alembic_config, "head")
    assert tables == [("alembic_version",)]


def test_migrations_match_models(alembic_config: Config) -> None:
    command.check(alembic_config)
