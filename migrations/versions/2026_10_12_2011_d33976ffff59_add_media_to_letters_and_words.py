"""add media to letters and words"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d33976ffff59"
down_revision: str | Sequence[str] | None = "a4aeb848335d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("letters", sa.Column("sound", sa.String(length=111), nullable=True))
    op.add_column(
        "letters",
        sa.Column("explanation_without_sign", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "letters",
        sa.Column("explanation_with_sign", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "letters", sa.Column("explanation_sound", sa.String(length=111), nullable=True)
    )
    op.add_column("words", sa.Column("image", sa.String(length=111), nullable=True))
    op.add_column("words", sa.Column("sound", sa.String(length=111), nullable=True))
    op.create_check_constraint(
        op.f("ck_letters_explanation_pair"),
        "letters",
        "(explanation_without_sign IS NULL) = (explanation_with_sign IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_letters_explanation_pair"), "letters", type_="check")
    op.drop_column("words", "sound")
    op.drop_column("words", "image")
    op.drop_column("letters", "explanation_sound")
    op.drop_column("letters", "explanation_with_sign")
    op.drop_column("letters", "explanation_without_sign")
    op.drop_column("letters", "sound")
