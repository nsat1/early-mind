from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
import pytest
from psycopg.types.json import Jsonb

pytestmark = pytest.mark.integration

MOSCOW = ZoneInfo("Europe/Moscow")
MONDAY = datetime(2026, 10, 5, 12, tzinfo=MOSCOW)
INSERT_EVENT = (
    "INSERT INTO analytics_events "
    "(name, schema_version, app_version, properties, received_at) "
    "VALUES (%s, 1, '1.0.0', %s, %s)"
)


@pytest.fixture
def events(app_connection: psycopg.Connection) -> Iterator[psycopg.Connection]:
    with app_connection.transaction(force_rollback=True):
        yield app_connection


def add(
    connection: psycopg.Connection,
    name: str,
    properties: dict[str, Any],
    received_at: datetime = MONDAY,
) -> None:
    connection.execute(INSERT_EVENT, (name, Jsonb(properties), received_at))


def session(duration: int, answers: int, strong: int) -> dict[str, int]:
    return {
        "duration_seconds": duration,
        "cards_opened": 3,
        "answers": answers,
        "correct_answers": answers,
        "learned_letters": 10,
        "strong_letters": strong,
    }


def test_weekly_sessions(events: psycopg.Connection) -> None:
    add(events, "session_finished", session(300, 0, 2))
    add(events, "session_finished", session(420, 5, 5))
    add(events, "session_finished", session(900, 3, 4))
    add(events, "app_opened", {"days_since_first_visit": "0"})

    rows = events.execute("SELECT * FROM analytics_weekly_sessions").fetchall()

    assert rows == [(date(2026, 10, 5), 3, 2, 420.0, Decimal("0.667"), 4.0)]


def test_weeks_follow_moscow_time(events: psycopg.Connection) -> None:
    add(
        events,
        "session_finished",
        session(60, 1, 0),
        datetime(2026, 10, 11, 23, tzinfo=MOSCOW),
    )
    add(
        events,
        "session_finished",
        session(60, 1, 0),
        datetime(2026, 10, 12, 0, tzinfo=MOSCOW),
    )

    rows = events.execute(
        "SELECT week, sessions FROM analytics_weekly_sessions ORDER BY week"
    ).fetchall()

    assert rows == [(date(2026, 10, 5), 1), (date(2026, 10, 12), 1)]


def test_letter_accuracy(events: psycopg.Connection) -> None:
    answers = [
        ("m", "sound", True),
        ("m", "sound", True),
        ("m", "sound", False),
        ("m", "picture", True),
        ("a", "sound", False),
    ]
    for code, task_type, correct in answers:
        properties = {
            "alphabet_id": "ru",
            "letter_code": code,
            "task_type": task_type,
            "correct": correct,
        }
        add(events, "answer_given", properties)

    rows = events.execute(
        "SELECT alphabet_id, letter_code, task_type, answers, correct_answers, "
        "accuracy FROM analytics_letter_accuracy ORDER BY letter_code, task_type"
    ).fetchall()

    assert rows == [
        ("ru", "a", "sound", 1, 0, Decimal("0.000")),
        ("ru", "m", "picture", 1, 1, Decimal("1.000")),
        ("ru", "m", "sound", 3, 2, Decimal("0.667")),
    ]


def test_retention(events: psycopg.Connection) -> None:
    opened = {
        "2026-W40": ["7-13"],
        "2026-W41": ["0", "0", "0", "0", "1", "1", "7-13"],
        "2026-W42": ["0", "0"],
    }
    for week, ranges in opened.items():
        for days in ranges:
            properties = {"days_since_first_visit": days, "first_visit_week": week}
            add(events, "app_opened", properties)

    rows = events.execute(
        "SELECT * FROM analytics_retention ORDER BY first_visit_week"
    ).fetchall()

    assert rows == [
        ("2026-W40", 0, 1, None),
        ("2026-W41", 4, 1, Decimal("0.250")),
        ("2026-W42", 2, 0, Decimal("0.000")),
    ]
