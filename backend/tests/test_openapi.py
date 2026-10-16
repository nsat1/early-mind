import json

from app.main import create_app
from app.openapi import OPENAPI_FILE


def test_openapi_file_is_up_to_date() -> None:
    stored = json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))

    assert stored == create_app().openapi(), (
        "Run: uv run --locked python -m app.openapi"
    )
