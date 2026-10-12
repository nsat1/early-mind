import tomllib
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.alphabet.models import (
    ALPHABET_ID_LENGTH,
    LETTER_CODE_LENGTH,
    MEDIA_PATH_LENGTH,
    WORD_LENGTH,
    LetterKind,
)

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "alphabets"
ALPHABET_FILE = "alphabet.toml"
SOUND_MAX_BYTES = 100 * 1024
IMAGE_MAX_BYTES = 150 * 1024

AlphabetId = Annotated[
    str, StringConstraints(pattern=r"^[a-z]+$", max_length=ALPHABET_ID_LENGTH)
]
LetterCode = Annotated[
    str, StringConstraints(pattern=r"^[a-z]+$", max_length=LETTER_CODE_LENGTH)
]
Symbol = Annotated[str, StringConstraints(min_length=1, max_length=1)]
Example = Annotated[str, StringConstraints(min_length=1, max_length=WORD_LENGTH)]
SoundPath = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-z0-9]+(?:[-/][a-z0-9]+)*\.mp3$", max_length=MEDIA_PATH_LENGTH
    ),
]
ImagePath = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-z0-9]+(?:[-/][a-z0-9]+)*\.(?:webp|svg)$",
        max_length=MEDIA_PATH_LENGTH,
    ),
]


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class WordSource(SourceModel):
    text: Example
    image: ImagePath | None = None
    sound: SoundPath | None = None


class LetterSource(SourceModel):
    code: LetterCode
    symbol: Symbol
    kind: LetterKind
    position: Annotated[int, Field(gt=0)]
    sound: SoundPath | None = None
    words: Annotated[list[WordSource], Field(min_length=1)]


class AlphabetSource(SourceModel):
    id: AlphabetId
    letters: Annotated[list[LetterSource], Field(min_length=1)]

    @model_validator(mode="after")
    def check_unique_letters(self) -> Self:
        for field in ("code", "position"):
            counts = Counter(getattr(letter, field) for letter in self.letters)
            duplicates = sorted(value for value, count in counts.items() if count > 1)
            if duplicates:
                raise ValueError(f"Duplicate letter {field}: {duplicates}")
        return self

    def media(self) -> Iterator[tuple[str, int]]:
        for letter in self.letters:
            sounds = [letter.sound, *(word.sound for word in letter.words)]
            images = [word.image for word in letter.words]
            yield from ((path, SOUND_MAX_BYTES) for path in sounds if path)
            yield from ((path, IMAGE_MAX_BYTES) for path in images if path)


def media_problems(alphabet: AlphabetSource, alphabet_dir: Path) -> list[str]:
    problems = []
    for path, max_bytes in alphabet.media():
        file = alphabet_dir / path
        if not file.is_file():
            problems.append(f"{path}: file not found")
        elif file.stat().st_size > max_bytes:
            problems.append(f"{path}: larger than {max_bytes} bytes")
    return problems


def alphabet_files(content_dir: Path = CONTENT_DIR) -> list[Path]:
    return sorted(content_dir.glob(f"*/{ALPHABET_FILE}"))


def load_alphabet(path: Path) -> AlphabetSource:
    with path.open("rb") as file:
        return AlphabetSource.model_validate(tomllib.load(file))
