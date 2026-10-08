"""add alphabet content schema"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "12876677c479"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alphabets",
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alphabets")),
    )
    op.create_table(
        "letters",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("alphabet_id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("vowel", "consonant", "sign", name="kind", native_enum=False),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('vowel', 'consonant', 'sign')", name=op.f("ck_letters_kind")
        ),
        sa.CheckConstraint("position > 0", name=op.f("ck_letters_position_positive")),
        sa.ForeignKeyConstraint(
            ["alphabet_id"],
            ["alphabets.id"],
            name=op.f("fk_letters_alphabet_id_alphabets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_letters")),
        sa.UniqueConstraint(
            "alphabet_id", "code", name=op.f("uq_letters_alphabet_id_code")
        ),
        sa.UniqueConstraint(
            "alphabet_id", "position", name=op.f("uq_letters_alphabet_id_position")
        ),
    )
    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("letter_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("position > 0", name=op.f("ck_words_position_positive")),
        sa.ForeignKeyConstraint(
            ["letter_id"],
            ["letters.id"],
            name=op.f("fk_words_letter_id_letters"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_words")),
        sa.UniqueConstraint(
            "letter_id", "position", name=op.f("uq_words_letter_id_position")
        ),
    )


def downgrade() -> None:
    op.drop_table("words")
    op.drop_table("letters")
    op.drop_table("alphabets")
