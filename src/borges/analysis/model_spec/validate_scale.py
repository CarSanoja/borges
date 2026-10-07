from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import DecisionRule
from borges.analysis.result_scale import detect_scale, is_proportion_rule
from borges.analysis.scale_check import is_difference_rule, is_ratio_rule

COUNT_FAMILIES = ("poisson", "quasipoisson", "negbin")


def scale_problems(spec: ModelSpecOutput, rule: DecisionRule | None) -> list[str]:
    if rule is None:
        return []
    if detect_scale(rule.metric) != 1.0:
        if spec.family == "ols" or spec.report == "marginal_effect":
            return []
        return [
            "the decision rule is a difference in proportions, which this family does not "
            "report as a coefficient; a logit reports it as report marginal_effect"
        ]
    if is_ratio_rule(rule) and (
        spec.family == "ols" or spec.report in ("coefficient", "marginal_effect")
    ):
        return ["the decision rule compares a ratio with 1.0, so report a ratio"]
    if spec.family in COUNT_FAMILIES and spec.report == "rate_ratio" and is_difference_rule(rule):
        return [
            "the decision rule compares a difference with 0, which a rate ratio does not report; "
            "use report marginal_effect for additional events per unit of the exposure"
        ]
    if spec.family == "logit" and spec.report != "marginal_effect" and is_proportion_rule(rule):
        return [
            "the decision rule is a difference in proportions, which a logit coefficient or odds "
            "ratio does not report; use report marginal_effect"
        ]
    return []
