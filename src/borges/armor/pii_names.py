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
ROLES = (
    "partner|manager|employee|customer|client|patient|student|teacher|doctor|physician|nurse|"
    "agent|advisor|adviser|applicant|borrower|owner|contact|member|user|staff|auditor|reviewer|"
    "seller|buyer|driver|worker|supervisor|officer|tenant|guardian|parent|"
    "cliente|paciente|alumno|estudiante|empleado|socio|medico|profesor|docente|titular|"
    "solicitante|asesor|vendedor|tutor"
)
ROLE_NAME = re.compile(rf"^(?:(?:{ROLES})(?:full|first|last)?name|nombre(?:del?)?(?:{ROLES}))$")


def is_name_header(column: str | None) -> bool:
    if not column:
        return False
    return re.sub(r"[\W_]+", "", str(column).lower()) in NAME_HEADERS


def is_role_name_header(column: str | None) -> bool:
    """partner_name in an audit file holds 60 partners over 900 engagements: a person named by
    role repeats, so the share of unique values does not apply to it. Bare "name" and "nombre"
    still need it, because they also head columns of storms and products."""
    if not column:
        return False
    return ROLE_NAME.match(re.sub(r"[\W_]+", "", str(column).lower())) is not None


def _capitalised_word(word: str) -> bool:
    letters = WORD_PUNCTUATION.sub("", word)
    stem = letters.rstrip("0123456789")
    if stem != letters and not any(c.islower() for c in stem):
        return False
    return bool(stem) and stem.isalpha() and word[0].isupper()


def is_name_value(text: str) -> bool:
    value = text.strip()
    if not value or len(value) > MAX_NAME_LENGTH:
        return False
    core = [w for w in value.split() if w not in PARTICLES]
    if not MIN_WORDS <= len(core) <= MAX_WORDS:
        return False
    return all(_capitalised_word(w) for w in core)


def values_look_like_names(
    values: Sequence[object], n_unique: int, n_rows: int, by_role: bool = False
) -> bool:
    texts = [v for v in values if isinstance(v, str) and v.strip()]
    if len(texts) < MIN_SAMPLES or n_rows <= 0:
        return False
    if n_unique < MIN_UNIQUE or (not by_role and n_unique / n_rows < MIN_UNIQUE_SHARE):
        return False
    return sum(is_name_value(t) for t in texts) / len(texts) >= MIN_SHARE
