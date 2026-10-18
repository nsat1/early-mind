import pytest
from fastapi.testclient import TestClient
from pydantic import HttpUrl

from app.auth.dependencies import app_origin

LOGOUT_URL = "/api/v1/auth/logout"


@pytest.mark.parametrize(
    ("app_url", "origin"),
    [
        ("http://localhost:5173", "http://localhost:5173"),
        ("https://early-mind.ru/", "https://early-mind.ru"),
        ("https://early-mind.ru:443", "https://early-mind.ru"),
        ("https://Early-Mind.ru:8443/app", "https://early-mind.ru:8443"),
    ],
)
def test_app_origin_keeps_scheme_host_and_custom_port(
    app_url: str, origin: str
) -> None:
    assert app_origin(HttpUrl(app_url)) == origin


@pytest.mark.integration
@pytest.mark.parametrize(
    "origin",
    [
        pytest.param("https://evil.example", id="other-site"),
        pytest.param("http://early-mind.example", id="other-scheme"),
        pytest.param("null", id="null"),
    ],
)
def test_unsafe_request_from_other_origin_is_rejected(
    client: TestClient, origin: str
) -> None:
    response = client.post(LOGOUT_URL, headers={"Origin": origin})

    assert response.status_code == 403
    assert response.json()["detail"] == "Request origin not allowed"
    assert "set-cookie" not in response.headers


@pytest.mark.integration
def test_unsafe_request_without_origin_is_rejected(client: TestClient) -> None:
    del client.headers["Origin"]

    assert client.post(LOGOUT_URL).status_code == 403


@pytest.mark.integration
def test_unsafe_request_from_app_origin_is_accepted(client: TestClient) -> None:
    assert client.post(LOGOUT_URL).status_code == 204


@pytest.mark.integration
def test_safe_request_is_not_checked(client: TestClient) -> None:
    del client.headers["Origin"]

    assert client.get("/api/v1/account").status_code == 401
