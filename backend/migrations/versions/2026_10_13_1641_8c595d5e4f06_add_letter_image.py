"""add letter image"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c595d5e4f06"
down_revision: str | Sequence[str] | None = "86aa24ab753c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("letters", sa.Column("image", sa.String(length=111), nullable=True))


def downgrade() -> None:
    op.drop_column("letters", "image")
