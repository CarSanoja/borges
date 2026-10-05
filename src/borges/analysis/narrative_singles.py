"""A count of single-change universes that flipped, checked against the garden.

A checkout summary at a491fe1 wrote "Two other single-change universes also flipped the verdict"
and then named one single change and one combination of three. A count that does not match the
garden's single-change flips is replaced by words that make no count.
"""

from __future__ import annotations

import re

from borges.analysis.narrative_counts import TOKEN, _value
from borges.garden.models import Garden, Report

SINGLES = re.compile(
    rf"\b{TOKEN}\s+(other\s+|more\s+|additional\s+)?single[- ]change\s+universes?\b",
    re.IGNORECASE,
)


def single_flips(garden: Garden) -> int:
    return sum(1 for u in garden.universes.values() if u.kind == "single" and u.flipped is True)


def restate_single_counts(report: Report, garden: Garden | None, narrative: str) -> str:
    if garden is None:
        return narrative
    flip = report.minimal_flip
    minimal = 1 if flip is not None and len(flip.changes) == 1 else 0
    singles = single_flips(garden)

    def fix(match: re.Match[str]) -> str:
        other = match.group(2) is not None
        expected = singles - minimal if other else singles
        if _value(match.group(1)) == expected:
            return match.group(0)
        words = "other universes" if other else "some universes"
        return words.capitalize() if match.group(0)[0].isupper() else words

    return SINGLES.sub(fix, narrative)
