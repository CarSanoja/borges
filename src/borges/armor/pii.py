from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from borges.armor.pii_patterns import DETECTORS, DOB_COLUMN, DOB_VALUE

TOKEN = "[redacted:{kind}]"
MAX_SCAN_CHARS = 20000


@dataclass(frozen=True)
class PiiMatch:
    kind: str
    start: int
    end: int


def is_dob_column(column: str | None) -> bool:
    return bool(column) and DOB_COLUMN.search(str(column)) is not None


def _raw_matches(text: str, column: str | None) -> list[PiiMatch]:
    found: list[PiiMatch] = []
    for detector in DETECTORS:
        for match in detector.pattern.finditer(text):
            if detector.validate is None or detector.validate(match.group(0)):
                found.append(PiiMatch(detector.kind, match.start(), match.end()))
    if is_dob_column(column):
        found.extend(
            PiiMatch("date_of_birth", m.start(), m.end()) for m in DOB_VALUE.finditer(text)
        )
    return found


def find_pii(text: str, column: str | None = None) -> list[PiiMatch]:
    if not text or len(text) < 5 and not is_dob_column(column):
        return []
    ordered = sorted(_raw_matches(text[:MAX_SCAN_CHARS], column), key=lambda m: (m.start, -m.end))
    kept: list[PiiMatch] = []
    cursor = -1
    for match in ordered:
        if match.start >= cursor:
            kept.append(match)
            cursor = match.end
    return kept


def redact_pii(text: str, column: str | None = None) -> str:
    matches = find_pii(text, column)
    if not matches:
        return text
    pieces: list[str] = []
    cursor = 0
    for match in matches:
        pieces.append(text[cursor : match.start])
        pieces.append(TOKEN.format(kind=match.kind))
        cursor = match.end
    pieces.append(text[cursor:])
    return "".join(pieces)


def count_pii(text: str, column: str | None = None) -> Counter[str]:
    return Counter(match.kind for match in find_pii(text, column))
