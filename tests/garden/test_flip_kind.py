from __future__ import annotations

import pytest

from borges.analysis.models import AnalysisResult, Comparator, DecisionRule
from borges.garden.models import Flip
from borges.garden.search import flip_kind


def result(estimate: float, p_value: float) -> AnalysisResult:
    return AnalysisResult(
        estimate=estimate, ci_low=estimate - 1, ci_high=estimate + 1, p_value=p_value, n=10
    )


@pytest.mark.parametrize(
    ("comparator", "baseline", "flipped", "expected"),
    [
        (Comparator.GT, result(0.5, 0.01), result(0.4, 0.2), "significance"),
        (Comparator.GT, result(0.5, 0.01), result(-0.1, 0.01), "direction"),
        (Comparator.LT, result(-0.5, 0.01), result(-0.4, 0.2), "significance"),
        (Comparator.LT, result(-0.5, 0.01), result(0.1, 0.01), "direction"),
        (Comparator.GT, result(-0.5, 0.2), result(0.5, 0.01), "direction"),
    ],
)
def test_flip_kind_respects_comparator(
    comparator: Comparator, baseline: AnalysisResult, flipped: AnalysisResult, expected: str
) -> None:
    rule = DecisionRule(metric="m", comparator=comparator, threshold=0.0)
    assert flip_kind(rule, baseline, flipped) == expected


def test_flip_kind_uses_threshold() -> None:
    rule = DecisionRule(metric="m", comparator=Comparator.GT, threshold=0.3)
    assert flip_kind(rule, result(0.5, 0.01), result(0.2, 0.01)) == "direction"
    assert flip_kind(rule, result(0.5, 0.01), result(0.35, 0.4)) == "significance"


def test_old_recording_without_kind_loads() -> None:
    payload = {
        "universe_id": "u",
        "changes": [],
        "baseline_result": result(1, 0.01).model_dump(),
        "flipped_result": result(-1, 0.01).model_dump(),
        "baseline_verdict": "SHIP",
        "flipped_verdict": "DON'T SHIP",
    }
    assert Flip.model_validate(payload).kind is None
