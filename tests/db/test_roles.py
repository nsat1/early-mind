from collections.abc import Iterator

import psycopg
import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import create_database

pytestmark = pytest.mark.integration


@pytest.fixture
def probe_table(migrator_connection: psycopg.Connection) -> Iterator[None]:
    migrator_connection.execute(
        "CREATE TABLE probe (id serial PRIMARY KEY, name text NOT NULL)"
    )
    yield
    migrator_connection.execute("DROP TABLE probe")


@pytest.mark.anyio
async def test_app_engine_connects_as_app_role(test_database: None) -> None:
    engine, sessions = create_database(Settings())
    try:
        async with sessions() as session:
            user = await session.scalar(text("SELECT current_user"))
    finally:
        await engine.dispose()
    assert user == "early_mind_app"


@pytest.mark.usefixtures("probe_table")
def test_app_role_modifies_rows(app_connection: psycopg.Connection) -> None:
    app_connection.execute("INSERT INTO probe (name) VALUES ('first')")
    app_connection.execute("UPDATE probe SET name = 'second'")
    rows = app_connection.execute("SELECT id, name FROM probe").fetchall()
    app_connection.execute("DELETE FROM probe")
    assert rows == [(1, "second")]


@pytest.mark.usefixtures("probe_table")
@pytest.mark.parametrize(
    "statement",
    [
        "TRUNCATE probe",
        "ALTER TABLE probe ADD COLUMN extra integer",
        "DROP TABLE probe",
        "CREATE TABLE extra (id integer)",
    ],
)
def test_app_role_cannot_change_schema(
    app_connection: psycopg.Connection, statement: str
) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app_connection.execute(statement)
