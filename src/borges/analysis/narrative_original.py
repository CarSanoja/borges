"""The original result and the adversary's part, stated from the report rather than by the model.

A narrator once described another universe as the original analysis (another estimate, sample
size and specification) and credited a pre-registered adversary with two specifications when no
adversary option had entered the garden. The original sentence is built here and required
verbatim; sentences that restate the original with other numbers, or describe adversary options
that do not exist, are dropped when the retry fails too.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import Report

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
ORIGINAL = re.compile(r"\b(?:original|primary|baseline)\b", re.I)
ADVERSARY = re.compile(r"\badversar", re.I)
DECIMAL = re.compile(r"\d+\.\d+")


def _num(value: float) -> str:
    return f"{value:.3g}"


def _p(value: float) -> str:
    return "p < 0.001" if value < 0.001 else f"p = {value:.2g}"


def original_sentence(report: Report) -> str:
    r = report.original_result
    return (
        f"The original analysis estimated {_num(r.estimate)} (95% CI {_num(r.ci_low)} to "
        f"{_num(r.ci_high)}, {_p(r.p_value)}, n = {r.n:,}) and returned the verdict "
        f"{report.original_verdict}."
    )


def _has_adversary(plan: AnalysisPlan) -> bool:
    return any(o.origin == "adversary" for s in plan.steps for o in s.options)


def original_problems(plan: AnalysisPlan, report: Report, narrative: str) -> list[str]:
    found = []
    if " ".join(original_sentence(report).split()) not in " ".join(narrative.split()):
        found.append(f"the original sentence is missing: {original_sentence(report)}")
    if not _has_adversary(plan) and ADVERSARY.search(narrative):
        found.append(
            "it describes adversary options, but no adversary option entered the garden; "
            "every universe uses the planner's options"
        )
    return found


def _unfounded(plan: AnalysisPlan, report: Report, sentence: str) -> bool:
    allowed = set(DECIMAL.findall(original_sentence(report)))
    restated = ORIGINAL.search(sentence) and set(DECIMAL.findall(sentence)) - allowed
    return bool(restated) or (not _has_adversary(plan) and bool(ADVERSARY.search(sentence)))


def with_original(plan: AnalysisPlan, report: Report, narrative: str) -> str:
    sentence = original_sentence(report)
    kept = [
        s
        for s in _SENTENCE_END.split(narrative.strip())
        if s and s != sentence and not _unfounded(plan, report, s)
    ]
    return " ".join([sentence, *kept])
