from __future__ import annotations

import re

from borges.analysis.models import DecisionRule
from borges.analysis.result_scale import is_proportion_rule
from borges.analysis.scale_check import is_difference_rule
from borges.analysis.schemas import ReviewVerdict

UNIT_DEMAND = re.compile(
    r"percentage[- ]points?|\bpp\b|[*x×]\s*100\b|times 100|multipl\w*\s+(?:\w+\s+){0,3}by\s+100|"
    r"\bby 100\b|\b100\s*[*x×]",
    re.IGNORECASE,
)
SENTENCE = re.compile(r"(?<=[.!?])\s+")
FOLLOW_UP = re.compile(
    r"^(?:this|that|these|those|it|such|thus|therefore|hence|so|which|as a result)\b", re.IGNORECASE
)
RATIO_DEMAND = re.compile(
    r"\bIRR\b|incidence[- ]rate ratio|rate ratio|odds ratio|exponentiat\w*|\bexp\(", re.IGNORECASE
)
IGNORED = "review point dropped: it asks for a unit conversion that the code contract forbids"


def _demand(rule: DecisionRule | None) -> re.Pattern[str]:
    """Under a rule on a difference the result check refuses a ratio, so a reviewer who asks for
    one can only lose the option: a hurricanes negative binomial template (597c38e) and a Poisson
    GLM in free code (2327203) were recoded to the IRR their specs named and then failed."""
    if rule is not None and (is_difference_rule(rule) or is_proportion_rule(rule)):
        return re.compile(f"{UNIT_DEMAND.pattern}|{RATIO_DEMAND.pattern}", re.IGNORECASE)
    return UNIT_DEMAND


def apply_unit_contract(verdict: ReviewVerdict, rule: DecisionRule | None = None) -> ReviewVerdict:
    demand = _demand(rule)
    if verdict.faithful or not verdict.problem or not demand.search(verdict.problem):
        return verdict
    kept: list[str] = []
    dropped = False
    for sentence in SENTENCE.split(verdict.problem.strip()):
        if demand.search(sentence) or (dropped and FOLLOW_UP.match(sentence)):
            dropped = True
            continue
        dropped = False
        kept.append(sentence)
    if kept:
        return verdict.model_copy(update={"problem": " ".join(kept)})
    return verdict.model_copy(update={"faithful": True, "problem": IGNORED})
