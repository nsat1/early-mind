import logging

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(
    request: pytest.FixtureRequest, test_database: None, test_redis: Settings
) -> Settings:
    return Settings(**getattr(request, "param", {}))


def test_ready_with_available_services(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("settings", [{"redis_host": "redis.invalid"}], indirect=True)
def test_ready_reports_unavailable_session_storage(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.health"):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "Session storage unavailable"
    assert caplog.messages == ["Session storage readiness check failed"]
