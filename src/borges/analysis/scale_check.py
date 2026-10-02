from __future__ import annotations

from collections.abc import Callable
from typing import Any

from borges.analysis.models import DecisionRule
from borges.analysis.result_scale import detect_scale

RATIO_WORDS = ("ratio",)


def is_ratio_rule(rule: DecisionRule) -> bool:
    return rule.threshold == 1.0 and any(word in rule.metric.lower() for word in RATIO_WORDS)


def scale_check(rule: DecisionRule) -> Callable[[dict[str, Any]], str | None] | None:
    if not is_ratio_rule(rule):
        return None

    def check(result: dict[str, Any]) -> str | None:
        estimate, low, high = result["estimate"], result["ci_low"], result["ci_high"]
        if min(estimate, low) > 0:
            return None
        return (
            f"the decision rule compares the {rule.metric} with 1.0, so estimate, ci_low and "
            f"ci_high must be ratios, which are always positive; got estimate {estimate:.4g} "
            f"and interval [{low:.4g}, {high:.4g}], which looks like a log-scale coefficient: "
            f"return exp(coefficient) and exp() of both interval limits"
        )

    return check


def scale_instruction(rule: DecisionRule) -> str:
    if detect_scale(rule.metric) != 1.0:
        return (
            f"Decision rule metric: {rule.metric}. Return estimate, ci_low and ci_high as a "
            f"difference in proportions (for example -0.0014), not in percentage points: "
            f"Borges converts units after your code runs."
        )
    text = (
        f"Decision rule: the estimate is compared with {rule.threshold:g} "
        f"({rule.comparator.value}); "
        f"metric: {rule.metric}. Return estimate, ci_low and ci_high on exactly that scale."
    )
    if is_ratio_rule(rule):
        text += " It is a ratio: exponentiate a log-odds or log-rate coefficient and both limits."
    return text
