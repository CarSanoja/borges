from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisResult
from borges.garden.degenerate import DEGENERATE_REASON, degenerate_message, is_degenerate


def res(estimate: float, low: float, high: float) -> AnalysisResult:
    return AnalysisResult(estimate=estimate, ci_low=low, ci_high=high, p_value=0.5, n=300)


VOTE = res(-0.7951, -1.3458, -0.2443)
MARP = res(0.0434, 0.025, 0.062)


def test_the_separated_window_of_fertility_vote_is_not_estimable() -> None:
    separated = res(-36.6228, -43415.2875, 43342.0419)
    assert is_degenerate(VOTE, separated)
    message = degenerate_message(VOTE, separated)
    assert message.startswith(DEGENERATE_REASON) and "78,763 times wider" in message


@pytest.mark.parametrize(
    ("baseline", "result"),
    [
        (MARP, res(4.0, 1.0, 7.0)),
        (res(0.001, -0.019, 0.021), res(1.0, -19.0, 21.0)),
        (VOTE, res(-0.05, -2.3, 2.2)),
        (VOTE, res(-1.1, -2.5, 0.16)),
        (res(0.0, -0.1, 0.1), res(0.0, -50.0, 50.0)),
    ],
)
def test_rescaled_small_or_null_results_are_kept(
    baseline: AnalysisResult, result: AnalysisResult
) -> None:
    assert not is_degenerate(baseline, result)
