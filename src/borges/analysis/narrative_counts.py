"""Counts of universes that the summary states. The red_cards summary at a0fe149 said "five of
eight universes (63%) retain BIAS DETECTED, while one combination reverses it" when seven of
eight did. A sentence whose count of universes, or the share beside it, matches no count of the
garden is dropped."""

from __future__ import annotations

import re

from borges.analysis.narrative_repeats import SENTENCE
from borges.garden.models import Report

WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
]
NUMBER_WORDS = {word: value for value, word in enumerate(WORDS)}
TOKEN = r"(\d+|" + "|".join(WORDS) + r")"
PAIR = re.compile(
    rf"\b{TOKEN}\s+(?:of|out of)\s+(?:the\s+|all\s+)?{TOKEN}\b(?=[^.;]*\buniverses?\b)",
    re.IGNORECASE,
)
PERCENT = re.compile(r"(\d+(?:\.\d+)?)%")


def _value(token: str) -> int:
    return int(token) if token.isdigit() else NUMBER_WORDS[token.lower()]


def _counts(report: Report) -> tuple[set[int], set[int]]:
    total, flipped = report.n_universes, report.n_flipped
    distinct = report.n_distinct_results or total
    share = report.robustness_beam if report.robustness_beam is not None else report.robustness
    agree = round(share * distinct)
    parts = {flipped, total - flipped, agree, distinct - agree, distinct, total}
    return parts, {total, distinct, total + report.n_failed}


def _shares(report: Report, parts: set[int], wholes: set[int]) -> set[int]:
    shares = {round(100 * part / whole) for part in parts for whole in wholes if whole}
    for value in (report.robustness, report.robustness_beam, report.robustness_design):
        if value is not None:
            shares |= {round(100 * value), round(100 * (1 - value))}
    return shares


def drop_wrong_counts(report: Report, narrative: str) -> str:
    parts, wholes = _counts(report)
    shares = _shares(report, parts, wholes)
    kept = []
    for sentence in SENTENCE.split(narrative.strip()):
        pairs = [(_value(a), _value(b)) for a, b in PAIR.findall(sentence)]
        wrong = any(part not in parts or whole not in wholes for part, whole in pairs)
        if pairs and not wrong:
            wrong = any(round(float(p)) not in shares for p in PERCENT.findall(sentence))
        if not wrong:
            kept.append(sentence)
    return " ".join(kept)
