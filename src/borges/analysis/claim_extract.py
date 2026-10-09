"""Read the result a user claims from the analysis text they bring; extract nothing when unsure."""

from __future__ import annotations

import re

from borges.analysis.claim_models import ClaimedResult, ClaimKind, Direction
from borges.analysis.claim_patterns import (
    DOWN,
    ESTIMATE,
    INTERVAL,
    LEVEL,
    NEGATOR,
    NONE,
    NOT_SIGNIFICANT,
    P_VALUE,
    SIGNIFICANT,
    UP,
    parse_number,
    sentences,
)

MAX_LEVEL_PCT = 10.0
RATIO_WORD = re.compile(r"ratio|razón|^(or|rr|hr|irr)$", re.IGNORECASE)
MARGINAL_WORD = re.compile(r"marginal|^ame$", re.IGNORECASE)
COEFFICIENT_WORD = re.compile(r"coef|beta|β|^b$", re.IGNORECASE)


def _kind(word: str) -> ClaimKind:
    if RATIO_WORD.search(word.strip()):
        return "ratio"
    if MARGINAL_WORD.search(word.strip()):
        return "marginal"
    if COEFFICIENT_WORD.search(word.strip()):
        return "coefficient"
    return "generic"


def _direction(estimate: float | None, kind: ClaimKind) -> Direction | None:
    if estimate is None:
        return None
    centre = 1.0 if kind == "ratio" else 0.0
    if estimate == centre:
        return "none"
    return "positive" if estimate > centre else "negative"


def _significance(sentence: str, after: int, result: ClaimedResult) -> None:
    pvalues = [m for m in P_VALUE.finditer(sentence)]
    later = [m for m in pvalues if m.start() >= after] or pvalues
    if later:
        value = parse_number(later[0].group("num"))
        operator = later[0].group("op").replace("==", "=")
        operator = {"≤": "<=", "≥": ">="}.get(operator, operator)
        if value is not None and 0.0 <= value <= 1.0:
            result.p_operator, result.p_value = operator, value
            return
    level = LEVEL.search(sentence)
    if level and SIGNIFICANT.search(sentence) and not NOT_SIGNIFICANT.search(sentence):
        pct = float(level.group("pct"))
        if 0.0 < pct <= MAX_LEVEL_PCT:
            result.p_operator, result.p_value = "<", pct / 100.0
            return
    if NOT_SIGNIFICANT.search(sentence):
        result.significant = False
    elif SIGNIFICANT.search(sentence):
        result.significant = True


def _interval(sentence: str, result: ClaimedResult) -> None:
    found = INTERVAL.search(sentence)
    if not found:
        return
    low, high = parse_number(found.group("low")), parse_number(found.group("high"))
    if low is not None and high is not None and low <= high:
        result.ci_low, result.ci_high = low, high


def _estimate_claim(sentence: str, match: re.Match[str]) -> ClaimedResult | None:
    estimate = parse_number(match.group("num"))
    if estimate is None:
        return None
    kind = _kind(match.group("word"))
    result = ClaimedResult(
        estimate=estimate,
        kind=kind,
        direction=_direction(estimate, kind),
        quote=sentence[:200],
    )
    _significance(sentence, match.end(), result)
    _interval(sentence, result)
    return result


def _candidates(text: str) -> list[tuple[str, ClaimedResult]]:
    found = []
    for sentence in sentences(text):
        for match in ESTIMATE.finditer(sentence):
            claim = _estimate_claim(sentence, match)
            if claim is not None:
                found.append((sentence, claim))
                break
    return found


def _worded(text: str, hints: list[str]) -> ClaimedResult | None:
    found: list[tuple[Direction, str]] = []
    for sentence in sentences(text):
        lowered = sentence.lower()
        if hints and not any(hint in lowered for hint in hints):
            continue
        ups, downs, none = UP.search(sentence), DOWN.search(sentence), NONE.search(sentence)
        if sum(bool(x) for x in (ups, downs, none)) != 1:
            continue
        if NEGATOR.search(sentence) and not none:
            continue
        direction: Direction = "positive" if ups else "negative" if downs else "none"
        found.append((direction, sentence))
    if len({direction for direction, _ in found}) != 1:
        return None
    direction, sentence = found[0]
    result = ClaimedResult(direction=direction, quote=sentence[:200])
    _significance(sentence, 0, result)
    if direction == "none" and result.significant is None and result.p_value is None:
        result.significant = False
    return result


def extract_claim(text: str, hints: list[str] | None = None) -> ClaimedResult | None:
    wanted = [hint.lower() for hint in hints or []]
    candidates = _candidates(text)
    if len({claim.estimate for _, claim in candidates}) > 1:
        tied = [c for s, c in candidates if any(hint in s.lower() for hint in wanted)]
        if len({claim.estimate for claim in tied}) != 1:
            return None
        return tied[0]
    if candidates:
        return candidates[0][1]
    return _worded(text, wanted)
