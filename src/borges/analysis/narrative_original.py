"""The original result and the adversary's part, checked against the report.

A narrator once described another universe as the original analysis (another estimate, sample
size and specification) and credited a pre-registered adversary with two specifications when no
adversary option had entered the garden. A sentence about the original whose decimals match none
of the original's values, and any account of adversary options when there are none, are errors
worth a retry; when the opening sentence does not carry the original estimate, the sentence built
here is put first instead.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.garden.models import AnalysisResult, Report

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
ORIGINAL = re.compile(
    r"\b(?:original|primary|baseline)\s+(?:analysis|estimate|estimand|result|model|effect)\b"
    r"(?!\s+(?:of|from|on)\s+(?:the\s+)?(?:flip|alternative))",
    re.I,
)
ADVERSARY = re.compile(r"\badversar", re.I)
DECIMAL = re.compile(r"-?\d+\.\d+")
NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?")


def _num(value: float) -> str:
    return f"{value:.3g}"


def _p(value: float) -> str:
    return "p < 0.001" if value < 0.001 else f"p = {value:.2g}"


def result_phrase(r: AnalysisResult) -> str:
    return (
        f"{_num(r.estimate)} (95% CI {_num(r.ci_low)} to {_num(r.ci_high)}, {_p(r.p_value)}, "
        f"n = {r.n:,})"
    )


def original_sentence(report: Report) -> str:
    return (
        f"The original analysis estimated {result_phrase(report.original_result)} and returned "
        f"the verdict {report.original_verdict}."
    )


def carries_value(text: str, value: float) -> bool:
    return any(_matches(t, value) for t in DECIMAL.findall(text))


def _matches(token: str, value: float) -> bool:
    places = len(token.split(".", 1)[1])
    return round(value, places) == float(token)


def _values(report: Report) -> list[float]:
    r = report.original_result
    return [r.estimate, r.ci_low, r.ci_high, r.p_value]


def carries_estimate(report: Report, sentence: str) -> bool:
    """A pay-gap narrative opened with the estimate as "-503", which has no decimals, and the
    built sentence was put in front of it, so the summary said the same thing twice. A rounding
    counts only when it keeps the magnitude: 0.0293 rounds to "0", the 0% of any share."""
    value = report.original_result.estimate
    if carries_value(sentence, value):
        return True
    shown = {_num(value)} | ({f"{value:,.0f}", str(round(value))} if abs(value) >= 100 else set())
    return any(token in shown for token in NUMBER.findall(sentence))


def _contradicts(report: Report, sentence: str) -> bool:
    tokens = DECIMAL.findall(sentence)
    if not ORIGINAL.search(sentence) or not tokens:
        return False
    return not any(_matches(t, v) for t in tokens for v in _values(report))


def _has_adversary(plan: AnalysisPlan) -> bool:
    return any(o.origin == "adversary" for s in plan.steps for o in s.options)


def _unfounded(plan: AnalysisPlan, report: Report, sentence: str) -> bool:
    invented = not _has_adversary(plan) and bool(ADVERSARY.search(sentence))
    return invented or _contradicts(report, sentence)


def original_problems(plan: AnalysisPlan, report: Report, narrative: str) -> list[str]:
    found = [
        f"it states the original analysis with numbers it does not have: {s}"
        for s in _SENTENCE_END.split(narrative.strip())
        if _contradicts(report, s)
    ]
    if not _has_adversary(plan) and ADVERSARY.search(narrative):
        found.append(
            "it describes adversary options, but no adversary option entered the garden; "
            "every universe uses the planner's options"
        )
    return found


def with_original(plan: AnalysisPlan, report: Report, narrative: str) -> str:
    kept = [
        s for s in _SENTENCE_END.split(narrative.strip()) if s and not _unfounded(plan, report, s)
    ]
    if kept and carries_estimate(report, kept[0]):
        return " ".join(kept)
    return " ".join([original_sentence(report), *kept])
