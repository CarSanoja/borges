from __future__ import annotations

import pytest

from borges.analysis.models import DecisionRule


def test_default_rule_has_no_problems() -> None:
    assert DecisionRule(metric="effect").problems() == []


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 2.0, float("nan"), float("inf")])
def test_alpha_outside_open_unit_interval_is_a_problem(alpha: float) -> None:
    assert any("alpha" in p for p in DecisionRule(metric="m", alpha=alpha).problems())


@pytest.mark.parametrize("threshold", [float("nan"), float("inf")])
def test_non_finite_threshold_is_a_problem(threshold: float) -> None:
    assert any("threshold" in p for p in DecisionRule(metric="m", threshold=threshold).problems())


def test_empty_metric_and_labels_are_problems() -> None:
    rule = DecisionRule(metric=" ", positive_label="", negative_label="no")
    assert len(rule.problems()) == 2
