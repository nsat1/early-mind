import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.core.errors import PROBLEM_MEDIA_TYPE


def test_unknown_path_returns_problem(client: TestClient) -> None:
    response = client.get("/missing")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "instance": "/missing",
    }


def test_wrong_method_keeps_allow_header(client: TestClient) -> None:
    response = client.post("/health")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.json()["title"] == "Method Not Allowed"


def test_invalid_parameter_returns_errors(client: TestClient) -> None:
    response = client.get("/api/v1/alphabets/ru/letters", params={"kind": "letter"})

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json() == {
        "type": "about:blank",
        "title": "Unprocessable Content",
        "status": 422,
        "detail": "Request parameters are invalid",
        "instance": "/api/v1/alphabets/ru/letters",
        "errors": [
            {
                "in": "query",
                "name": "kind",
                "detail": "Input should be 'vowel', 'consonant' or 'sign'",
            }
        ],
    }


def test_unavailable_database_returns_service_unavailable(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.core.errors"):
        response = client.get("/api/v1/alphabets/ru/letters")

    assert response.status_code == 503
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json() == {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "Database unavailable",
        "instance": "/api/v1/alphabets/ru/letters",
    }
    assert caplog.messages == ["Database unavailable"]


@pytest.mark.parametrize(
    ("error", "status", "title"),
    [
        (PoolTimeoutError("pool exhausted"), 503, "Service Unavailable"),
        (RuntimeError("secret internals"), 500, "Internal Server Error"),
    ],
)
def test_unhandled_error_hides_details(
    app: FastAPI, error: Exception, status: int, title: str
) -> None:
    async def fail() -> None:
        raise error

    app.add_api_route("/fail", fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/fail")

    assert response.status_code == status
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
    assert response.json()["title"] == title
    assert str(error) not in response.text


def test_openapi_describes_errors_as_problems(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/api/v1/alphabets/{alphabet_id}/letters"]["get"][
        "responses"
    ]
    for status in ("404", "422", "503"):
        [(media_type, content)] = responses[status]["content"].items()
        assert media_type == PROBLEM_MEDIA_TYPE
        assert content["schema"] == {"$ref": "#/components/schemas/Problem"}
        assert content["example"]["status"] == int(status)
    assert "HTTPValidationError" not in schema["components"]["schemas"]
