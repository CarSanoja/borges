"""A summary that announces a minimal flip the report does not have.

A checkout summary at 9b95d04 opened its second sentence with "A minimal flip was found" when the
only flips re-included rows the plan's notes mark as invalid, so the report named none, and later
sentences called the same flip contaminated. With no minimal flip in the report, the claim is
rewritten to say the flip found is contaminated, or dropped when the report has no flip at all. A
bank summary at a491fe1 echoed the report field ("the minimal flip is null") and added "there is
no re-execution to report"; both are dropped, as is "the minimal flip is absent" (red_cards at
027d581). A checkout summary at 70a6102 wrote "reversed that verdict: the minimal flip is null." and
kept a stray colon.
"""

from __future__ import annotations

import re

from borges.garden.models import Report

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
CLAIM = re.compile(
    r"\b(?:a|the)\s+minimal\s+flip\s+(?:was|is|has\s+been)\s+found\b|\bfound\s+a\s+minimal\s+flip\b",
    re.IGNORECASE,
)
CONTAMINATED = "The only flip found is contaminated"
NULL_FLIP = re.compile(
    r"\s*[;,:\u2014]?\s*(?:and\s+)?the\s+minimal\s+flip\s+is\s+(?:null|none|empty|absent|missing)\b",
    re.IGNORECASE,
)
NOTHING_TO_REPORT = re.compile(r"\bno\s+re-?execution\s+to\s+report\b", re.IGNORECASE)


def _contaminated(report: Report) -> bool:
    return report.contaminated_flip is not None or bool(report.contaminated_flips)


def claimed_flips(report: Report, narrative: str) -> list[str]:
    if report.minimal_flip is not None:
        return []
    return [s for s in _SENTENCE_END.split(narrative.strip()) if CLAIM.search(s)]


def no_flip_problems(report: Report, narrative: str) -> list[str]:
    reason = (
        "its only flips re-include rows the plan's notes mark as invalid"
        if _contaminated(report)
        else "no change reversed the verdict"
    )
    return [
        f"it says a minimal flip was found, but the report has none ({reason}): {s}"
        for s in claimed_flips(report, narrative)
    ]


def rewrite_claimed_flips(report: Report, narrative: str) -> str:
    kept: list[str] = []
    for sentence in _SENTENCE_END.split(narrative.strip()):
        if report.minimal_flip is None:
            sentence = "" if NOTHING_TO_REPORT.search(sentence) else NULL_FLIP.sub("", sentence)
            sentence = sentence.strip() if sentence.strip(" .") else ""
        if sentence and sentence in claimed_flips(report, sentence):
            if not _contaminated(report):
                continue
            sentence = CLAIM.sub(CONTAMINATED, sentence, count=1)
            sentence = sentence[0].upper() + sentence[1:]
        if sentence:
            kept.append(sentence)
    return " ".join(kept)
