from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from borges.armor.pii_fold import fold_with_map
from borges.armor.pii_patterns import DETECTORS, DOB_COLUMN, DOB_VALUE

TOKEN = "[redacted:{kind}]"
MAX_SCAN_CHARS = 2_000_000
UNSCANNED_TOKEN = "[redacted:unscanned]"


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
    folded, origin = fold_with_map(text[:MAX_SCAN_CHARS])
    raw = _raw_matches(folded, column)
    ordered = sorted(
        (PiiMatch(m.kind, origin[m.start], origin[m.end - 1] + 1) for m in raw),
        key=lambda m: (m.start, -m.end),
    )
    kept: list[PiiMatch] = []
    cursor = -1
    for match in ordered:
        if match.start >= cursor:
            kept.append(match)
            cursor = match.end
    return kept


def redact_pii(text: str, column: str | None = None) -> str:
    unscanned = len(text) > MAX_SCAN_CHARS
    head = text[:MAX_SCAN_CHARS]
    matches = find_pii(head, column)
    if not matches and not unscanned:
        return text
    pieces: list[str] = []
    cursor = 0
    for match in matches:
        pieces.append(head[cursor : match.start])
        pieces.append(TOKEN.format(kind=match.kind))
        cursor = match.end
    pieces.append(head[cursor:])
    if unscanned:
        pieces.append(UNSCANNED_TOKEN)
    return "".join(pieces)


def count_pii(text: str, column: str | None = None) -> Counter[str]:
    return Counter(match.kind for match in find_pii(text, column))
