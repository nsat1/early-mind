"""align content schema with data model"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "82c14fa1b622"
down_revision: str | Sequence[str] | None = "12876677c479"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "alphabets", "id", new_column_name="alphabet_id", type_=sa.String(10)
    )
    op.alter_column("letters", "id", new_column_name="letter_id")
    op.alter_column("letters", "alphabet_id", type_=sa.String(10))
    op.alter_column("letters", "code", type_=sa.String(20))
    op.alter_column("letters", "symbol", type_=sa.String(1))
    op.alter_column("words", "id", new_column_name="word_id")
    op.alter_column("words", "text", new_column_name="example", type_=sa.String(50))


def downgrade() -> None:
    op.alter_column("words", "example", new_column_name="text", type_=sa.String())
    op.alter_column("words", "word_id", new_column_name="id")
    op.alter_column("letters", "symbol", type_=sa.String())
    op.alter_column("letters", "code", type_=sa.String())
    op.alter_column("letters", "alphabet_id", type_=sa.String())
    op.alter_column("letters", "letter_id", new_column_name="id")
    op.alter_column("alphabets", "alphabet_id", new_column_name="id", type_=sa.String())
