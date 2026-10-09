from __future__ import annotations

import re
from collections.abc import Sequence

PERSON_NAME_KIND = "person_name"
NAME_HEADERS = frozenset(
    {
        "fullname",
        "firstname",
        "lastname",
        "middlename",
        "surname",
        "familyname",
        "givenname",
        "employeename",
        "customername",
        "clientname",
        "patientname",
        "studentname",
        "contactname",
        "apellido",
        "apellidos",
        "nombrecompleto",
    }
)
PARTICLES = frozenset(
    {"de", "del", "la", "las", "los", "van", "von", "der", "den", "da", "di", "du", "y", "e"}
)
WORD_PUNCTUATION = re.compile(r"['’.-]")
MIN_WORDS = 2
MAX_WORDS = 4
MIN_SAMPLES = 3
MIN_SHARE = 0.8
MIN_UNIQUE = 10
MIN_UNIQUE_SHARE = 0.5
MAX_NAME_LENGTH = 60


def is_name_header(column: str | None) -> bool:
    if not column:
        return False
    return re.sub(r"[\W_]+", "", str(column).lower()) in NAME_HEADERS


def _capitalised_word(word: str) -> bool:
    letters = WORD_PUNCTUATION.sub("", word)
    return bool(letters) and letters.isalpha() and word[0].isupper()


def is_name_value(text: str) -> bool:
    value = text.strip()
    if not value or len(value) > MAX_NAME_LENGTH:
        return False
    core = [w for w in value.split() if w not in PARTICLES]
    if not MIN_WORDS <= len(core) <= MAX_WORDS:
        return False
    return all(_capitalised_word(w) for w in core)


def values_look_like_names(values: Sequence[object], n_unique: int, n_rows: int) -> bool:
    texts = [v for v in values if isinstance(v, str) and v.strip()]
    if len(texts) < MIN_SAMPLES or n_rows <= 0:
        return False
    if n_unique < MIN_UNIQUE or n_unique / n_rows < MIN_UNIQUE_SHARE:
        return False
    return sum(is_name_value(t) for t in texts) / len(texts) >= MIN_SHARE
