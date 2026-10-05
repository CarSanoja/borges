"""Review points about the dummies Borges listed in place of a level get_dummies drops.

A checkout covariate option at 6525b47 named platform_ios and platform_android with
drop_first=True. get_dummies dropped android, the harness listed the dummies it built (ios and
web), and the reviewer twice called the option unfaithful for listing web, so the option was lost
although the adjustment is the same whichever level is the reference.
"""

from __future__ import annotations

import re

from borges.analysis.models import DecisionRule
from borges.analysis.review_contract import FOLLOW_UP, SENTENCE, apply_unit_contract
from borges.analysis.schemas import ReviewVerdict

DUMMY_NOTE = "ctx['covariates'] named dummies get_dummies did not build ("
LISTED = "the ones it built are listed instead ("
DUMMY_TALK = re.compile(
    r"drop_first|reference (?:level|category)|first (?:level|category)|dumm(?:y|ies)",
    re.IGNORECASE,
)
IGNORED_DUMMIES = (
    "review point dropped: it concerns the dummies Borges listed in place of the level "
    "get_dummies drops, which leaves the adjustment unchanged"
)


def _names(note: str) -> list[str]:
    names: list[str] = []
    for marker in (DUMMY_NOTE, LISTED):
        if marker in note:
            listed = note.split(marker, 1)[1].split(")", 1)[0]
            names.extend(name.strip() for name in listed.split(",") if name.strip())
    return names


def apply_dummy_contract(verdict: ReviewVerdict, note: str | None) -> ReviewVerdict:
    if verdict.faithful or not verdict.problem or not note or DUMMY_NOTE not in note:
        return verdict
    names = _names(note)

    def about(sentence: str) -> bool:
        if DUMMY_TALK.search(sentence):
            return True
        return any(re.search(rf"\b{re.escape(name)}\b", sentence) for name in names)

    kept: list[str] = []
    dropped = False
    for sentence in SENTENCE.split(verdict.problem.strip()):
        if about(sentence) or (dropped and FOLLOW_UP.match(sentence)):
            dropped = True
            continue
        dropped = False
        kept.append(sentence)
    if kept:
        return verdict.model_copy(update={"problem": " ".join(kept)})
    return verdict.model_copy(update={"faithful": True, "problem": IGNORED_DUMMIES})


def apply_contracts(
    verdicts: list[ReviewVerdict], notes: dict[str, str | None], rule: DecisionRule | None
) -> list[ReviewVerdict]:
    return [
        apply_dummy_contract(apply_unit_contract(v, rule), notes.get(v.option_id)) for v in verdicts
    ]
