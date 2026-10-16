from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import PROBLEM_MEDIA_TYPE
from app.main import create_app

SOUND = b"ID3 letter sound"


@pytest.fixture
def media_client(settings: Settings, tmp_path: Path) -> Iterator[TestClient]:
    letters = tmp_path / "ru" / "letters"
    letters.mkdir(parents=True)
    (letters / "m.mp3").write_bytes(SOUND)
    (tmp_path / "ru" / "alphabet.toml").write_text('id = "ru"', encoding="utf-8")
    with TestClient(create_app(settings, content_dir=tmp_path)) as client:
        yield client


def test_media_file_is_served(media_client: TestClient) -> None:
    response = media_client.get("/media/ru/letters/m.mp3?v=3fa2c1d4")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == SOUND


def test_media_file_supports_ranges(media_client: TestClient) -> None:
    response = media_client.get(
        "/media/ru/letters/m.mp3", headers={"range": "bytes=0-2"}
    )

    assert response.status_code == 206
    assert response.content == SOUND[:3]


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/media/ru/letters/missing.mp3", id="missing-file"),
        pytest.param("/media/ru/alphabet.toml", id="content-file"),
    ],
)
def test_only_existing_media_is_served(media_client: TestClient, path: str) -> None:
    response = media_client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM_MEDIA_TYPE
