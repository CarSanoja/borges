from __future__ import annotations

from borges.analysis.models import AnalysisResult, DecisionRule
from borges.cli_inconclusive import inconclusive_clause, is_inconclusive, smallest_p
from borges.garden.models import Garden, Universe

RULE = DecisionRule(
    metric="m", alpha=0.05, positive_label="YES", negative_label="NO CLEAR EVIDENCE"
)


def result(p_value: float) -> AnalysisResult:
    return AnalysisResult(estimate=0.3, ci_low=-2.0, ci_high=2.6, p_value=p_value, n=275)


def universe(uid: str, p_value: float, kind: str = "single", status: str = "done") -> Universe:
    done = status == "done"
    return Universe(
        id=uid,
        choices={},
        kind=kind,
        status=status,
        result=result(p_value) if done else None,
    )


def test_negative_verdict_with_p_at_or_above_alpha_is_inconclusive() -> None:
    assert is_inconclusive("NO CLEAR EVIDENCE", result(0.82), RULE)
    assert is_inconclusive("NO CLEAR EVIDENCE", result(0.05), RULE)


def test_significant_negative_or_positive_verdict_is_not_inconclusive() -> None:
    assert not is_inconclusive("NO CLEAR EVIDENCE", result(0.001), RULE)
    assert not is_inconclusive("YES", result(0.9), RULE)
    assert not is_inconclusive("NO CLEAR EVIDENCE", result(0.9), None)


def test_smallest_p_uses_completed_universes_without_verifications() -> None:
    garden = Garden()
    for item in (
        universe("a", 0.82, "baseline"),
        universe("b", 0.07),
        universe("c", 0.0001, "verification"),
        universe("d", 0.0001, status="pending"),
    ):
        garden.add(item)
    assert smallest_p(garden) == 0.07
    assert smallest_p(Garden()) is None


def test_clause_states_that_no_path_reached_alpha() -> None:
    text = inconclusive_clause(0.0712, 0.05, 32, 32)
    expected = "32 of 32 paths are also inconclusive: no path reached p < 0.05; "
    assert text == expected + "smallest p-value 0.0712"


def test_clause_does_not_claim_alpha_was_missed_when_a_path_reached_it() -> None:
    text = inconclusive_clause(0.01, 0.05, 30, 32)
    assert "no path reached" not in text and "smallest p-value 0.01" in text
