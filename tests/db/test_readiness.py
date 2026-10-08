import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def settings(test_database: None) -> Settings:
    return Settings()


def test_ready_with_available_database(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
