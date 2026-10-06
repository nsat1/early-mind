from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_returns_ok(app: FastAPI) -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
