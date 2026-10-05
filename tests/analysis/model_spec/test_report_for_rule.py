from __future__ import annotations

from borges.analysis.model_spec.report_for_rule import report_for_rule
from borges.analysis.model_spec.validate import validate_spec
from borges.analysis.models import Comparator, DecisionRule
from tests.analysis.model_spec.data import make_spec

DEATHS = DecisionRule(metric="additional deaths", comparator=Comparator.GT, threshold=0.0)
RATIO = DecisionRule(metric="incidence rate ratio", comparator=Comparator.GT, threshold=1.0)
SHARE = DecisionRule(
    metric="difference in conversion rate (percentage points)",
    comparator=Comparator.GT,
    threshold=0.0,
)


def test_a_count_model_on_a_difference_rule_reports_the_marginal_effect() -> None:
    spec = make_spec("negbin", report="rate_ratio")
    fixed = report_for_rule(spec, DEATHS)
    assert fixed.report == "marginal_effect"
    assert not any("rate ratio" in p for p in validate_spec(fixed, ["y_count", "x"], None, DEATHS))


def test_a_ratio_rule_or_a_moderated_model_is_left_alone() -> None:
    spec = make_spec("poisson", report="rate_ratio")
    assert report_for_rule(spec, RATIO) is spec
    moderated = make_spec("poisson", report="rate_ratio", moderator="m")
    assert report_for_rule(moderated, DEATHS) is moderated


def test_a_logit_on_a_difference_in_proportions_reports_the_marginal_effect() -> None:
    assert report_for_rule(make_spec("logit", report="odds_ratio"), SHARE).report == (
        "marginal_effect"
    )
