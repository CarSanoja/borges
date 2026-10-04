from __future__ import annotations

from borges.analysis.model_spec.validate_standardized import standardized_problems
from borges.analysis.models import Comparator, DecisionRule
from tests.analysis.model_spec.data import make_spec

BETA = DecisionRule(
    metric="standardised coefficient of religiosity on well-being",
    comparator=Comparator.GT,
    threshold=0.0,
)


def test_a_standardised_metric_needs_the_outcome_and_exposure_z_scored() -> None:
    half = make_spec("ols", outcome="y_cont", exposure="x", standardize=["x"])
    [problem] = standardized_problems(half, BETA)
    assert "'y_cont'" in problem and "'x'" not in problem
    full = make_spec("ols", outcome="y_cont", exposure="x", standardize=["x", "y_cont"])
    assert standardized_problems(full, BETA) == []


def test_an_interaction_also_z_scores_the_moderator() -> None:
    spec = make_spec("ols", outcome="y_cont", exposure="x", moderator="m", standardize=["y_cont"])
    [problem] = standardized_problems(spec, BETA)
    assert "'x'" in problem and "'m'" in problem


def test_other_metrics_and_families_are_left_alone() -> None:
    raw = DecisionRule(metric="additional deaths", comparator=Comparator.GT, threshold=0.0)
    assert standardized_problems(make_spec("ols", outcome="y_cont", exposure="x"), raw) == []
    assert standardized_problems(make_spec("logit", outcome="y_bin", exposure="x"), BETA) == []
    smd = DecisionRule(metric="standardised mean difference", comparator=Comparator.GT)
    only_y = make_spec("ols", outcome="y_cont", exposure="x", standardize=["y_cont"])
    assert standardized_problems(only_y, smd) == []
