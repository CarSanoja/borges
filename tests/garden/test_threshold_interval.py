from __future__ import annotations

from borges.analysis.models import AnalysisResult, Comparator, DecisionRule
from borges.garden.threshold_interval import threshold_interval_caveats

HALF = DecisionRule(metric="points per weekly tutoring hour", threshold=0.5)
FEWER = DecisionRule(
    metric="rate ratio of exceptions, new versus old", comparator=Comparator.LT, threshold=0.8
)


def result(estimate: float, low: float, high: float, p: float = 1e-9) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=low, ci_high=high, p_value=p, n=600)


def test_an_interval_that_reaches_the_threshold_is_named() -> None:
    [note] = threshold_interval_caveats(HALF, result(0.678, 0.462, 0.895))
    assert "compares the estimate 0.678 with 0.5" in note
    assert "its p-value tests no effect (0)" in note
    assert "the data show an effect but not that it is past 0.5" in note


def test_an_interval_past_the_threshold_or_a_zero_threshold_gives_no_note() -> None:
    assert threshold_interval_caveats(HALF, result(0.9, 0.6, 1.2)) == []
    assert threshold_interval_caveats(FEWER, result(0.694, 0.656, 0.734)) == []
    zero = DecisionRule(metric="points", threshold=0.0)
    assert threshold_interval_caveats(zero, result(0.3, -0.1, 0.7, p=0.2)) == []


def test_a_ratio_interval_that_reaches_its_threshold_is_named() -> None:
    [note] = threshold_interval_caveats(FEWER, result(0.74, 0.66, 0.83))
    assert "its p-value tests no effect (1)" in note
