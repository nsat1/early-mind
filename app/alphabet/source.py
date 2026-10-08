import tomllib
from collections import Counter
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.alphabet.models import LetterKind

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "alphabets"

Code = Annotated[str, StringConstraints(pattern=r"^[a-z]+$")]
Symbol = Annotated[str, StringConstraints(min_length=1, max_length=1)]
Text = Annotated[str, StringConstraints(min_length=1)]


class LetterSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: Code
    symbol: Symbol
    kind: LetterKind
    position: Annotated[int, Field(gt=0)]
    words: Annotated[list[Text], Field(min_length=1)]


class AlphabetSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Code
    letters: list[LetterSource]

    @model_validator(mode="after")
    def check_unique_letters(self) -> Self:
        for field in ("code", "position"):
            counts = Counter(getattr(letter, field) for letter in self.letters)
            duplicates = sorted(value for value, count in counts.items() if count > 1)
            if duplicates:
                raise ValueError(f"Duplicate letter {field}: {duplicates}")
        return self


def load_alphabet(path: Path) -> AlphabetSource:
    with path.open("rb") as file:
        return AlphabetSource.model_validate(tomllib.load(file))
