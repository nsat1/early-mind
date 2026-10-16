from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.analytics.events import APP_OPENED, SESSION_FINISHED

URL = "/api/v1/analytics/events"


def with_properties(event: dict[str, Any], **changes: object) -> dict[str, Any]:
    return event | {"properties": event["properties"] | changes}


@pytest.mark.parametrize(
    ("events", "name", "error"),
    [
        pytest.param([APP_OPENED] * 51, "", "at most 50 items", id="large-batch"),
        pytest.param(
            [APP_OPENED | {"name": "page_viewed"}], "0", "tag", id="unknown-name"
        ),
        pytest.param(
            [APP_OPENED | {"device_id": "abc"}],
            "0.app_opened.device_id",
            "Extra inputs",
            id="extra-field",
        ),
        pytest.param(
            [with_properties(SESSION_FINISHED, duration_seconds=425)],
            "0.session_finished.properties.duration_seconds",
            "multiple of 10",
            id="unrounded-duration",
        ),
        pytest.param(
            [with_properties(SESSION_FINISHED, correct_answers=11)],
            "0.session_finished.properties",
            "correct_answers must not exceed answers",
            id="too-many-correct",
        ),
        pytest.param(
            [with_properties(SESSION_FINISHED, strong_letters=13)],
            "0.session_finished.properties",
            "strong_letters must not exceed learned_letters",
            id="too-many-strong",
        ),
    ],
)
def test_invalid_events_are_rejected(
    client: TestClient, events: list[dict[str, Any]], name: str, error: str
) -> None:
    response = client.post(URL, json=events)

    assert response.status_code == 422
    [problem_error] = response.json()["errors"]
    assert (problem_error["in"], problem_error["name"]) == ("body", name)
    assert error in problem_error["detail"]
