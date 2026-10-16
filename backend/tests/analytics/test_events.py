from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from tests.analytics.events import ANSWER_GIVEN, APP_OPENED, SESSION_FINISHED

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(test_database: None) -> Settings:
    return Settings()


@pytest.fixture
def stored_events(app_connection: psycopg.Connection) -> Iterator[psycopg.Connection]:
    yield app_connection
    app_connection.execute("DELETE FROM analytics_events")


def test_events_are_committed(
    client: TestClient, stored_events: psycopg.Connection
) -> None:
    batch = [APP_OPENED, SESSION_FINISHED, ANSWER_GIVEN]

    response = client.post("/api/v1/analytics/events", json=batch)

    assert response.status_code == 202
    assert response.content == b""
    rows = stored_events.execute(
        "SELECT name, schema_version, app_version, properties, received_at "
        "FROM analytics_events ORDER BY analytics_event_id"
    ).fetchall()
    assert [row[:4] for row in rows] == [
        (item["name"], item["schema_version"], item["app_version"], item["properties"])
        for item in batch
    ]
    now = datetime.now(UTC)
    for *_, received_at in rows:
        assert received_at == received_at.replace(minute=0, second=0, microsecond=0)
        assert now - timedelta(hours=1) < received_at <= now
