from __future__ import annotations

from borges.analysis.models import Comparator, DecisionRule
from borges.analysis.planner_measure import linear_odds_options, linear_odds_shortfall
from borges.analysis.schemas import PlannedOption, PlannedStep

ODDS = DecisionRule(
    metric="odds ratio of subscribing per call", comparator=Comparator.LT, threshold=1
)
DIFFERENCE = DecisionRule(metric="difference in conversion rate")


def model(*labels: str) -> PlannedStep:
    options = [
        PlannedOption(id=f"m{i}", label=label, rationale="r", spec="s", is_default=i == 0)
        for i, label in enumerate(labels)
    ]
    return PlannedStep(id="fit", title="Model", kind="model", description="d", options=options)


def test_a_linear_model_under_an_odds_ratio_rule_is_named() -> None:
    steps = [model("OLS linear probability model with HC3 SEs", "Logistic regression")]
    assert linear_odds_options(steps, ODDS) == ["fit.m0"]
    shortfall = linear_odds_shortfall(steps, ODDS)
    assert shortfall is not None and "fit.m0" in shortfall and "logistic" in shortfall


def test_logistic_labels_and_other_rules_pass() -> None:
    steps = [model("Logistic regression with cluster-robust SEs", "Probit with HC1 errors")]
    assert linear_odds_options(steps, ODDS) == []
    assert linear_odds_options([model("OLS with HC3 SEs")], DIFFERENCE) == []
    assert linear_odds_options([model("OLS with HC3 SEs")], None) == []
