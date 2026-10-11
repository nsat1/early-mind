import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "name"),
    [
        pytest.param("/api/v1/alphabets/RU/letters", "alphabet_id", id="uppercase-id"),
        pytest.param(
            f"/api/v1/alphabets/{'a' * 11}/letters", "alphabet_id", id="long-id"
        ),
        pytest.param("/api/v1/alphabets/ru/letters/A", "code", id="uppercase-code"),
        pytest.param("/api/v1/alphabets/ru/letters/а", "code", id="cyrillic-code"),
        pytest.param(
            f"/api/v1/alphabets/ru/letters/{'a' * 21}", "code", id="long-code"
        ),
    ],
)
def test_invalid_path_parameter_is_rejected(
    client: TestClient, path: str, name: str
) -> None:
    response = client.get(path)

    assert response.status_code == 422
    assert [(error["in"], error["name"]) for error in response.json()["errors"]] == [
        ("path", name)
    ]
