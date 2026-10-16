from typing import Any

APP_OPENED: dict[str, Any] = {
    "name": "app_opened",
    "schema_version": 1,
    "app_version": "1.0.0",
    "properties": {"days_since_first_visit": "7-13", "first_visit_week": "2026-W41"},
}
SESSION_FINISHED: dict[str, Any] = {
    "name": "session_finished",
    "schema_version": 1,
    "app_version": "1.0.0",
    "properties": {
        "duration_seconds": 420,
        "cards_opened": 6,
        "answers": 10,
        "correct_answers": 8,
        "learned_letters": 12,
        "strong_letters": 5,
    },
}
ANSWER_GIVEN: dict[str, Any] = {
    "name": "answer_given",
    "schema_version": 1,
    "app_version": "1.0.0",
    "properties": {
        "alphabet_id": "ru",
        "letter_code": "m",
        "task_type": "sound",
        "correct": True,
    },
}
