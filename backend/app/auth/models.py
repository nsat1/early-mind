import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMAIL_LENGTH = 254
PASSWORD_HASH_LENGTH = 128
POLICY_VERSION_LENGTH = 20


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    account_id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("uuidv7()")
    )
    email: Mapped[str] = mapped_column(String(EMAIL_LENGTH), unique=True)
    password_hash: Mapped[str] = mapped_column(String(PASSWORD_HASH_LENGTH))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class Consent(Base):
    __tablename__ = "consents"

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.account_id", ondelete="CASCADE"), primary_key=True
    )
    policy_version: Mapped[str] = mapped_column(
        String(POLICY_VERSION_LENGTH), primary_key=True
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
