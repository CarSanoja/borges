from __future__ import annotations

import json
from pathlib import Path

from borges.analysis.models import AnalysisResult, DecisionRule
from borges.cli_render import robustness_line, summary_lines
from borges.garden.models import Garden, Report, Universe
from borges.runs.models import RunSnapshot

CASES = Path(__file__).resolve().parents[1] / "cases"


def fertility_rule() -> DecisionRule:
    raw = json.loads((CASES / "fertility_religiosity" / "case.json").read_text(encoding="utf-8"))
    return DecisionRule.model_validate(raw["decision_rule"])


def make_result(p_value: float) -> AnalysisResult:
    return AnalysisResult(estimate=0.27, ci_low=-2.05, ci_high=2.6, p_value=p_value, n=275)


def make_report(verdict: str, p_value: float, flipped: int = 0) -> Report:
    return Report(
        question="q",
        original_verdict=verdict,
        original_result=make_result(p_value),
        minimal_flip=None,
        influences=[],
        robustness=1.0,
        n_universes=32,
        n_flipped=flipped,
        n_distinct_results=32,
    )


def test_inconclusive_original_result_says_the_paths_are_also_inconclusive() -> None:
    line = robustness_line(make_report("NO CLEAR EVIDENCE", 0.82), fertility_rule(), 0.0712)
    assert "32 of 32 paths are also inconclusive" in line
    assert "no path reached p < 0.05; smallest p-value 0.0712" in line
    assert "100%" not in line


def test_positive_original_result_keeps_the_percentage() -> None:
    rule = fertility_rule()
    line = robustness_line(make_report(rule.positive_label, 0.01), rule, 0.01)
    assert line.startswith("Robustness: 100% (share of distinct results)")


def test_significant_negative_verdict_keeps_the_percentage() -> None:
    rule = fertility_rule()
    line = robustness_line(make_report(rule.negative_label, 0.001), rule, 0.001)
    assert line.startswith("Robustness: 100%")


def test_without_a_rule_the_line_is_unchanged() -> None:
    assert robustness_line(make_report("NO CLEAR EVIDENCE", 0.82)).startswith("Robustness: 100%")


def test_summary_computes_the_smallest_p_from_the_garden() -> None:
    garden = Garden()
    garden.add(
        Universe(id="u1", choices={}, kind="baseline", status="done", result=make_result(0.82))
    )
    garden.add(
        Universe(id="u2", choices={}, kind="single", status="done", result=make_result(0.31))
    )
    snapshot = RunSnapshot(
        run_id="r",
        status="completed",
        decision_rule=fertility_rule(),
        garden=garden,
        report=make_report("NO CLEAR EVIDENCE", 0.82),
    )
    text = "\n".join(summary_lines(snapshot))
    assert "32 of 32 paths are also inconclusive: no path reached p < 0.05;" in text
    assert "smallest p-value 0.31" in text
