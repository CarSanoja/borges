"""The ratio a universe reports, read from the model that fitted it.

A bank summary at 508fe2e put a Poisson option's 0.896 in one range with the logit's odds ratios
(0.854 to 0.907), and red_cards compares a Poisson rate ratio with a logit odds ratio. On a binary
outcome a rate ratio is a risk ratio, another measure of the association, so its distance from an
odds ratio is partly the change of measure.
"""

from __future__ import annotations

import re

from borges.analysis.models import AnalysisPlan
from borges.analysis.scale_check import ratio_shaped
from borges.garden.models import Garden, Universe
from borges.garden.noop import single_universe

RATIO_MEASURES = {
    "Logit": "odds ratio",
    "Binomial": "odds ratio",
    "Poisson": "rate ratio",
    "NegativeBinomial": "rate ratio",
    "NegativeBinomialP": "rate ratio",
    "GeneralizedPoisson": "rate ratio",
}
FAMILY_MODELS = ("GLM", "GEE")


def reported_measure(universe: Universe) -> str | None:
    result = universe.result
    if result is None or not ratio_shaped(result.estimate, result.ci_low, result.ci_high):
        return None
    for trace in reversed(universe.traces):
        design = trace.design
        if design and design.get("model"):
            model = design["model"]
            name = design.get("family") if model in FAMILY_MODELS else model
            return RATIO_MEASURES.get(str(name))
    return None


def _a(measure: str) -> str:
    return f"an {measure}" if measure[0] in "aeiou" else f"a {measure}"


def measure_detail(baseline: Universe, universe: Universe) -> str | None:
    before, after = reported_measure(baseline), reported_measure(universe)
    if before is None or after is None or before == after:
        return None
    return (
        f"reports {_a(after)} where the original analysis reports {_a(before)}: another measure "
        "of the association, so this is an estimand change, not a re-analysis of the same quantity"
    )


def measure_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    baseline = garden.baseline
    if baseline is None or reported_measure(baseline) is None:
        return []
    found = []
    for step in plan.decision_steps:
        for option in step.options:
            single = single_universe(garden, step.id, option.id)
            if option.id == step.default.id or single is None:
                continue
            after, before = reported_measure(single), reported_measure(baseline)
            if after is not None and after != before:
                found.append(
                    f"The option '{option.label}' ({step.id}) reports {_a(after)} where the "
                    f"original analysis reports {_a(str(before))}: its estimates are another "
                    "measure of the association, so their distance from the original estimate is "
                    "partly the change of measure, not only of the analysis."
                )
    return found


STATED = (
    ("odds ratio", re.compile(r"\bodds\s+ratio", re.IGNORECASE)),
    ("rate ratio", re.compile(r"\b(?:incidence\s+)?rate\s+ratio", re.IGNORECASE)),
)


def stated_measure(plan: AnalysisPlan) -> str | None:
    """red_cards states an odds ratio of a red card per game; the planner often fits a Poisson."""
    found = [name for name, pattern in STATED if pattern.search(plan.decision_rule.metric)]
    return found[0] if len(found) == 1 else None


def rule_measure_caveats(plan: AnalysisPlan, garden: Garden) -> list[str]:
    stated = stated_measure(plan)
    fitted = reported_measure(garden.baseline) if garden.baseline is not None else None
    if stated is None or fitted is None or stated == fitted:
        return []
    return [
        f"The decision rule is stated as {_a(stated)}, but the original analysis fits a model "
        f"that reports {_a(fitted)}: the verdict applies the rule's threshold to {_a(fitted)}, "
        "another measure of the association."
    ]
