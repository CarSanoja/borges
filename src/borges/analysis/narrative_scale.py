"""Sentences that read a log-scale original estimate as units of the outcome.

A hurricanes summary at 068fa85 opened with "a one-unit increase in the femininity rating is
associated with 0.024 additional expected deaths" for a model of log1p(alldeaths). The scale
caveat was in the report and another sentence named log1p, so the check that the summary mentions
the log scale passed. A sentence that carries the original estimate, speaks of additional or more
of something and says nothing of a log scale or a percentage reads the estimate as units.
"""

from __future__ import annotations

import re

from borges.analysis.narrative_original import carries_estimate
from borges.garden.models import Report
from borges.garden.outcome_scale import LOG_WORDS

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
UNITS = re.compile(r"\b(?:additional|extra)\b|\b(?:more|fewer)\b(?!\s+than)", re.IGNORECASE)


def unit_readings(report: Report, narrative: str, scale: str | None) -> list[str]:
    if scale is None:
        return []
    return [
        s
        for s in _SENTENCE_END.split(narrative.strip())
        if carries_estimate(report, s) and UNITS.search(s) and not LOG_WORDS.search(s)
    ]


def drop_unit_readings(report: Report, narrative: str, scale: str | None) -> str:
    wrong = set(unit_readings(report, narrative, scale))
    return " ".join(s for s in _SENTENCE_END.split(narrative.strip()) if s and s not in wrong)
