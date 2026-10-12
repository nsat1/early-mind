"""add analytics metric views"""

from collections.abc import Sequence

from alembic import op

revision: str = "a4aeb848335d"
down_revision: str | Sequence[str] | None = "f7356100d69e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WEEKLY_SESSIONS = """
CREATE VIEW analytics_weekly_sessions AS
SELECT
    date_trunc('week', received_at AT TIME ZONE 'Europe/Moscow')::date AS week,
    count(*) AS sessions,
    count(*) FILTER (
        WHERE (properties ->> 'answers')::integer > 0
    ) AS completed_sessions,
    percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (properties ->> 'duration_seconds')::integer
    ) AS median_duration_seconds,
    round(
        avg(((properties ->> 'duration_seconds')::integer BETWEEN 300 AND 600)::integer),
        3
    ) AS healthy_duration_share,
    percentile_cont(0.5) WITHIN GROUP (
        ORDER BY (properties ->> 'strong_letters')::integer
    ) AS median_strong_letters
FROM analytics_events
WHERE name = 'session_finished'
GROUP BY 1
"""

LETTER_ACCURACY = """
CREATE VIEW analytics_letter_accuracy AS
SELECT
    date_trunc('week', received_at AT TIME ZONE 'Europe/Moscow')::date AS week,
    properties ->> 'alphabet_id' AS alphabet_id,
    properties ->> 'letter_code' AS letter_code,
    properties ->> 'task_type' AS task_type,
    count(*) AS answers,
    count(*) FILTER (WHERE (properties ->> 'correct')::boolean) AS correct_answers,
    round(avg((properties ->> 'correct')::boolean::integer), 3) AS accuracy
FROM analytics_events
WHERE name = 'answer_given'
GROUP BY 1, 2, 3, 4
"""

RETENTION = """
CREATE VIEW analytics_retention AS
SELECT
    properties ->> 'first_visit_week' AS first_visit_week,
    count(*) FILTER (
        WHERE properties ->> 'days_since_first_visit' = '0'
    ) AS new_devices,
    count(*) FILTER (
        WHERE properties ->> 'days_since_first_visit' = '7-13'
    ) AS returned_devices,
    round(
        count(*) FILTER (WHERE properties ->> 'days_since_first_visit' = '7-13')
        / nullif(
            count(*) FILTER (WHERE properties ->> 'days_since_first_visit' = '0'),
            0
        )::numeric,
        3
    ) AS return_rate
FROM analytics_events
WHERE name = 'app_opened'
GROUP BY 1
"""


def upgrade() -> None:
    op.execute(WEEKLY_SESSIONS)
    op.execute(LETTER_ACCURACY)
    op.execute(RETENTION)


def downgrade() -> None:
    op.execute("DROP VIEW analytics_retention")
    op.execute("DROP VIEW analytics_letter_accuracy")
    op.execute("DROP VIEW analytics_weekly_sessions")
