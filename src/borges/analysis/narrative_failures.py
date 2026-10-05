"""Sentences that explain why universes failed, replaced by the report's own account.

A red_cards summary at 508fe2e put three failed universes down to singular-matrix errors; one was
a process stopped with exit code -1. The report's caveat names each failing option and error, so
a summary sentence about failed universes is replaced by that caveat.
"""

from __future__ import annotations

import re

from borges.garden.models import Report

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
COUNT = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|several|some|all)"
FAILURE = re.compile(
    rf"\b{COUNT}\s+(?:of\s+the\s+)?(?:\w+\s+)?universes?\s+(?:\w+\s+){{0,3}}?"
    r"(?:failed|could\s+not\s+(?:run|be\s+run|complete)|crashed|errored)\b|\bfailed\s+universes?\b",
    re.IGNORECASE,
)
CAVEAT = re.compile(r"^\d+ universes? could not run and (?:is|are) left out of the robustness")


def failure_caveat(report: Report) -> str | None:
    return next((c for c in report.caveats if CAVEAT.match(c)), None)


def restate_failures(report: Report, narrative: str) -> str:
    caveat = failure_caveat(report)
    if caveat is None:
        return narrative
    kept: list[str] = []
    replaced = False
    for sentence in _SENTENCE_END.split(narrative.strip()):
        if not FAILURE.search(sentence):
            kept.append(sentence)
        elif not replaced:
            kept.append(caveat[0].upper() + caveat[1:])
            replaced = True
    return " ".join(kept)
