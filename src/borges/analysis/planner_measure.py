"""Model options that cannot report the measure the decision rule reads.

A bank plan at 7885ab7 made its default model "OLS linear probability model with HC3 SEs" under a
rule that reads an odds ratio, with a spec that exponentiated the linear coefficient: the template
fitted a logit, so the baseline ran a logit under an OLS label. A linear model reports a difference
of probabilities, and exp of its coefficient is no odds ratio. The planner is asked to make such
options logistic or drop them.
"""

from __future__ import annotations

import re

from borges.analysis.models import DecisionRule
from borges.analysis.schemas import PlannedStep

ODDS_RATIO = re.compile(r"\bodds\s+ratio", re.IGNORECASE)
LINEAR = re.compile(
    r"linear probability|\bLPM\b|^\s*(?:OLS|ordinary least squares|linear regression)\b",
    re.IGNORECASE,
)
LOGISTIC = re.compile(r"\blogit\b|\blogistic\b|\bprobit\b", re.IGNORECASE)


def linear_odds_options(steps: list[PlannedStep], rule: DecisionRule | None) -> list[str]:
    if rule is None or not ODDS_RATIO.search(rule.metric):
        return []
    return [
        f"{s.id}.{o.id}"
        for s in steps
        if s.kind == "model"
        for o in s.options
        if LINEAR.search(o.label) and not LOGISTIC.search(o.label)
    ]


def linear_odds_shortfall(steps: list[PlannedStep], rule: DecisionRule | None) -> str | None:
    found = linear_odds_options(steps, rule)
    if not found:
        return None
    return (
        "The decision rule reads an odds ratio, which only a logistic model reports, but these "
        f"model options name a linear model: {', '.join(found)}. A linear probability model "
        "reports a difference of probabilities, and exp of its coefficient is no odds ratio; make "
        "each a logistic model (for example with other standard errors), or drop it."
    )
