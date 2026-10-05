from __future__ import annotations

from borges.analysis.model_spec.percent_outcome import percent_outcome
from borges.analysis.models import DecisionRule
from tests.analysis.model_spec.data import make_spec

POINTS = DecisionRule(metric="conversion lift, treatment minus control (percentage points)")
RATIO = DecisionRule(metric="odds ratio", threshold=1.0)


def test_a_column_times_100_under_a_points_rule_is_the_column() -> None:
    for outcome in ("converted * 100", "100*converted", "(converted) * 100.0"):
        spec = make_spec("ols", outcome=outcome)
        assert percent_outcome(spec, POINTS, ["converted", "variant"]).outcome == "converted"


def test_other_rules_and_unknown_columns_are_left_alone() -> None:
    spec = make_spec("ols", outcome="converted * 100")
    assert percent_outcome(spec, RATIO, ["converted"]).outcome == "converted * 100"
    assert percent_outcome(spec, POINTS, ["revenue"]).outcome == "converted * 100"
    plain = make_spec("ols", outcome="converted")
    assert percent_outcome(plain, POINTS, ["converted"]).outcome == "converted"
