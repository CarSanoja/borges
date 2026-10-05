"""The report a decision rule needs, set when the spec asks for a ratio instead.

A hurricanes negative binomial option at 508fe2e reported a rate ratio for a rule on additional
deaths; its retry kept the ratio, the template was skipped, and the free code written instead
failed on a text covariate and was dropped. A count model on a difference rule, or a logit on a
difference in proportions, reports the marginal effect.
"""

from __future__ import annotations

from borges.analysis.model_spec.schema import ModelSpecOutput
from borges.analysis.models import DecisionRule
from borges.analysis.result_scale import detect_scale, is_proportion_rule
from borges.analysis.scale_check import is_difference_rule

COUNT_FAMILIES = ("poisson", "quasipoisson", "negbin")


def _needs_marginal(spec: ModelSpecOutput, rule: DecisionRule) -> bool:
    if spec.family in COUNT_FAMILIES and spec.report == "rate_ratio":
        return is_difference_rule(rule)
    if spec.family == "logit" and spec.report in ("coefficient", "odds_ratio"):
        return is_proportion_rule(rule) or detect_scale(rule.metric) != 1.0
    return False


def report_for_rule(spec: ModelSpecOutput, rule: DecisionRule | None) -> ModelSpecOutput:
    if rule is None or not spec.supported or spec.moderator is not None or spec.cov_type == "gee":
        return spec
    if not _needs_marginal(spec, rule):
        return spec
    return spec.model_copy(update={"report": "marginal_effect"})
