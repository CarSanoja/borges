from __future__ import annotations

import re

from borges.analysis.schemas import ReviewVerdict

UNIT_DEMAND = re.compile(
    r"percentage[- ]points?|\bpp\b|[*x×]\s*100\b|times 100|multipl\w*\s+(?:\w+\s+){0,3}by\s+100|"
    r"\bby 100\b|\b100\s*[*x×]",
    re.IGNORECASE,
)
SENTENCE = re.compile(r"(?<=[.!?])\s+")
IGNORED = "review point dropped: it asks for a unit conversion that the code contract forbids"


def apply_unit_contract(verdict: ReviewVerdict) -> ReviewVerdict:
    if verdict.faithful or not verdict.problem or not UNIT_DEMAND.search(verdict.problem):
        return verdict
    kept = [s for s in SENTENCE.split(verdict.problem.strip()) if not UNIT_DEMAND.search(s)]
    if kept:
        return verdict.model_copy(update={"problem": " ".join(kept)})
    return verdict.model_copy(update={"faithful": True, "problem": IGNORED})
