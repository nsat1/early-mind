import json
from pathlib import Path

from app.main import create_app

OPENAPI_FILE = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"


def render_openapi() -> str:
    return json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    OPENAPI_FILE.parent.mkdir(exist_ok=True)
    OPENAPI_FILE.write_text(render_openapi(), encoding="utf-8")


if __name__ == "__main__":
    main()
