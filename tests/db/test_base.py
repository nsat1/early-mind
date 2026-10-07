from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

from app.db.base import Base


def test_constraint_names_follow_convention() -> None:
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)
    Table("parents", metadata, Column("id", Integer, primary_key=True))
    children = Table(
        "children",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey("parents.id"), index=True),
        Column("nickname", String),
        Column("age", Integer),
        UniqueConstraint("parent_id", "nickname"),
        CheckConstraint("age >= 0", name="age_non_negative"),
    )

    names = {item.name for item in (*children.constraints, *children.indexes)}
    assert names == {
        "pk_children",
        "fk_children_parent_id_parents",
        "uq_children_parent_id_nickname",
        "ix_children_parent_id",
        "ck_children_age_non_negative",
    }
