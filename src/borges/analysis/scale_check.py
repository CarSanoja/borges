from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from borges.analysis.models import DecisionRule
from borges.analysis.result_scale import detect_scale, mentions_ratio, reads_probability


def is_ratio_rule(rule: DecisionRule) -> bool:
    return rule.threshold > 0 and mentions_ratio(rule.metric)


def is_difference_rule(rule: DecisionRule) -> bool:
    return rule.threshold == 0.0 and not mentions_ratio(rule.metric)


def ratio_shaped(estimate: float, low: float, high: float) -> bool:
    if min(estimate, low, high) <= 0:
        return False
    multiplicative = abs(math.sqrt(low * high) - estimate) <= 1e-6 * estimate
    additive = abs((low + high) / 2 - estimate) <= 1e-6 * estimate
    return multiplicative and not additive


def _difference_check(rule: DecisionRule) -> Callable[[dict[str, Any]], str | None]:
    def check(result: dict[str, Any]) -> str | None:
        estimate, low, high = result["estimate"], result["ci_low"], result["ci_high"]
        if not ratio_shaped(estimate, low, high):
            return None
        return (
            f"the decision rule compares the {rule.metric} with 0, so the estimate must be a "
            f"difference whose sign shows the direction; got estimate {estimate:.4g} with "
            f"interval [{low:.4g}, {high:.4g}], which is a ratio (exp of a coefficient) and is "
            f"always positive: return the coefficient and its interval without exponentiating"
        )

    return check


def scale_check(rule: DecisionRule) -> Callable[[dict[str, Any]], str | None] | None:
    if is_difference_rule(rule):
        return _difference_check(rule)
    if not is_ratio_rule(rule):
        return None

    def check(result: dict[str, Any]) -> str | None:
        estimate, low, high = result["estimate"], result["ci_low"], result["ci_high"]
        if min(estimate, low) > 0:
            return None
        return (
            f"the decision rule compares the {rule.metric} with {rule.threshold:g}, so estimate, "
            f"ci_low and "
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
    elif reads_probability(rule.metric):
        text += (
            " It is a change in a probability: a Logit coefficient is on the log-odds scale and a"
            " Probit one on the z scale, about 1.6 times smaller on the same data, and neither is"
            " a probability. Report the average marginal effect,"
            ' result.get_margeff(at="overall").summary_frame().loc[name], for every model.'
        )
    return text
