"""Whether an option's spec keeps the estimand is the judge's call, made before the code exists.

fertility_vote on 7 October: the judge accepted "only married as committed" and "dating counts as
committed" as other ways to measure the same interaction (0.6 each). The code reviewer then
compared each with the default's grouping, called the difference an estimand change and the
options were dropped without a repair, although their code did what their own specs said. Married
only is the change that, computed in advance, moves the published vote result to p .052. For an
option the judge accepted, an estimand flag on code that follows its spec is dropped, and on code
that does not it becomes a faithfulness problem the coder can repair.
"""

from __future__ import annotations

from borges.analysis.models import Option
from borges.analysis.schemas import ReviewVerdict


def settle_estimand(verdict: ReviewVerdict, option: Option) -> ReviewVerdict:
    if not verdict.changes_estimand or option.defensibility is None:
        return verdict
    problem = verdict.problem if not verdict.faithful else ""
    return verdict.model_copy(update={"changes_estimand": False, "problem": problem})
