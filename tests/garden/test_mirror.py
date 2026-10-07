from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisResult
from borges.garden.mirror import MIRROR_REASON, is_mirror, mirror_message


def result(estimate: float, low: float, high: float, p: float, n: int) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=low, ci_high=high, p_value=p, n=n)


START = result(-1.6230, -2.7236, -0.5225, 0.003847, 303)
LOW_CODED = result(1.6229, 0.5224, 2.7235, 0.003849, 303)


def test_the_starting_point_with_the_other_group_coded_1_is_the_same_analysis() -> None:
    """fertility_vote on 7 October, run 29: 'interaction = low_fert * committed' was reported
    as the smallest flip."""
    assert is_mirror(START, LOW_CODED, 0.0)
    assert mirror_message(START, LOW_CODED).startswith(MIRROR_REASON)


def test_an_odds_ratio_inverted_on_the_same_rows_is_the_same_analysis() -> None:
    odds = result(2.0, 1.25, 3.2, 0.004, 120)
    assert is_mirror(odds, result(0.5, 1 / 3.2, 1 / 1.25, 0.004, 120), 1.0)


@pytest.mark.parametrize(
    "other",
    [
        result(1.6229, 0.5224, 2.7235, 0.003849, 279),
        result(1.6229, 0.5224, 2.7235, 0.0100, 303),
        result(1.1000, 0.1000, 2.1000, 0.003849, 303),
        result(-0.9236, -2.0259, 0.1787, 0.1005, 279),
    ],
)
def test_a_different_analysis_is_not_a_mirror(other: AnalysisResult) -> None:
    assert not is_mirror(START, other, 0.0)


def test_a_mirror_needs_a_null_it_knows() -> None:
    assert not is_mirror(START, LOW_CODED, 0.5)
