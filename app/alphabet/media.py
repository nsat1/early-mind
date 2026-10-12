import os
from pathlib import PurePosixPath

from starlette.staticfiles import StaticFiles

MEDIA_URL = "/media"
MEDIA_SUFFIXES = frozenset({".mp3", ".webp", ".svg"})


class MediaFiles(StaticFiles):
    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        if PurePosixPath(path).suffix not in MEDIA_SUFFIXES:
            return "", None
        return super().lookup_path(path)


def media_url(alphabet_id: str, path: str | None) -> str | None:
    if path is None:
        return None
    return f"{MEDIA_URL}/{alphabet_id}/{path}"
