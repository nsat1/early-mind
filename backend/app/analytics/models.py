from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Identity,
    Index,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

APP_VERSION_LENGTH = 20


class AnalyticsEventName(StrEnum):
    APP_OPENED = "app_opened"
    SESSION_FINISHED = "session_finished"
    ANSWER_GIVEN = "answer_given"


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        CheckConstraint("schema_version > 0", name="schema_version_positive"),
        Index(None, "name", "received_at"),
    )

    analytics_event_id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    name: Mapped[AnalyticsEventName] = mapped_column(
        Enum(
            AnalyticsEventName,
            name="name",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda names: [name.value for name in names],
        )
    )
    schema_version: Mapped[int] = mapped_column(SmallInteger)
    app_version: Mapped[str] = mapped_column(String(APP_VERSION_LENGTH))
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("date_trunc('hour', now())")
    )
