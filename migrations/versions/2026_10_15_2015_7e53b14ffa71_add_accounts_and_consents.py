"""add accounts and consents"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7e53b14ffa71"
down_revision: str | Sequence[str] | None = "8c595d5e4f06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column(
            "account_id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False
        ),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "email = lower(email)", name=op.f("ck_accounts_email_lowercase")
        ),
        sa.PrimaryKeyConstraint("account_id", name=op.f("pk_accounts")),
        sa.UniqueConstraint("email", name=op.f("uq_accounts_email")),
    )
    op.create_table(
        "consents",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("policy_version", sa.String(length=20), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name=op.f("fk_consents_account_id_accounts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "account_id", "policy_version", name=op.f("pk_consents")
        ),
    )


def downgrade() -> None:
    op.drop_table("consents")
    op.drop_table("accounts")
