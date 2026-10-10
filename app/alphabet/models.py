from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Identity,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ALPHABET_ID_LENGTH = 10
LETTER_CODE_LENGTH = 20
WORD_LENGTH = 50


class LetterKind(StrEnum):
    VOWEL = "vowel"
    CONSONANT = "consonant"
    SIGN = "sign"


class Alphabet(Base):
    __tablename__ = "alphabets"

    alphabet_id: Mapped[str] = mapped_column(
        String(ALPHABET_ID_LENGTH), primary_key=True
    )


class Letter(Base):
    __tablename__ = "letters"
    __table_args__ = (
        UniqueConstraint("alphabet_id", "code"),
        UniqueConstraint("alphabet_id", "position"),
        CheckConstraint("position > 0", name="position_positive"),
    )

    letter_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    alphabet_id: Mapped[str] = mapped_column(
        String(ALPHABET_ID_LENGTH),
        ForeignKey("alphabets.alphabet_id", ondelete="CASCADE"),
    )
    code: Mapped[str] = mapped_column(String(LETTER_CODE_LENGTH))
    symbol: Mapped[str] = mapped_column(String(1))
    kind: Mapped[LetterKind] = mapped_column(
        Enum(
            LetterKind,
            name="kind",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda kinds: [kind.value for kind in kinds],
        )
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    words: Mapped[list[Word]] = relationship(
        order_by="Word.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("letter_id", "position"),
        CheckConstraint("position > 0", name="position_positive"),
    )

    word_id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    letter_id: Mapped[int] = mapped_column(
        ForeignKey("letters.letter_id", ondelete="CASCADE")
    )
    example: Mapped[str] = mapped_column(String(WORD_LENGTH))
    position: Mapped[int] = mapped_column(SmallInteger)
