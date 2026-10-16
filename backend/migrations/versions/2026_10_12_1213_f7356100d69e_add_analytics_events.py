"""add analytics events"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f7356100d69e"
down_revision: str | Sequence[str] | None = "82c14fa1b622"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column(
            "analytics_event_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.Enum(
                "app_opened",
                "session_finished",
                "answer_given",
                name="name",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column("app_version", sa.String(length=20), nullable=False),
        sa.Column(
            "properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("date_trunc('hour', now())"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "name IN ('app_opened', 'session_finished', 'answer_given')",
            name=op.f("ck_analytics_events_name"),
        ),
        sa.CheckConstraint(
            "schema_version > 0",
            name=op.f("ck_analytics_events_schema_version_positive"),
        ),
        sa.PrimaryKeyConstraint("analytics_event_id", name=op.f("pk_analytics_events")),
    )
    op.create_index(
        op.f("ix_analytics_events_name_received_at"),
        "analytics_events",
        ["name", "received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_analytics_events_name_received_at"), table_name="analytics_events"
    )
    op.drop_table("analytics_events")
