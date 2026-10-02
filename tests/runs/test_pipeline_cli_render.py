from __future__ import annotations

from borges.analysis.models import AnalysisResult, CodingSummary
from borges.cli_render import coding_line, search_line
from borges.garden.models import Report, SearchSummary


def test_search_line_states_the_budget() -> None:
    line = search_line(
        SearchSummary(
            levels_explored=2,
            max_combinations_per_level=10,
            universe_budget=40,
            universes_used=31,
            budget_exhausted=False,
        )
    )
    assert "31 of 40 universes used" in line
    assert "2 levels explored" in line and "10 combinations per level" in line
    assert "ran out" not in line


def test_search_line_flags_an_exhausted_budget() -> None:
    line = search_line(
        SearchSummary(levels_explored=1, universe_budget=5, universes_used=5, budget_exhausted=True)
    )
    assert "1 level explored" in line and "budget ran out before the search finished" in line


def test_coding_line_counts_smoke_and_repairs() -> None:
    line = coding_line(CodingSummary(options=9, smoke_tested=8, repaired_after_smoke=2, failed=1))
    assert "9 options" in line and "8 smoke-tested" in line
    assert "2 repaired" in line and "1 failed" in line


def test_report_loads_without_search_or_coding() -> None:
    result = AnalysisResult(estimate=0.1, ci_low=0, ci_high=0.2, p_value=0.01, n=5)
    report = Report.model_validate(
        {
            "question": "q",
            "original_verdict": "SHIP",
            "original_result": result.model_dump(),
            "minimal_flip": None,
            "influences": [],
            "robustness": 1.0,
            "n_universes": 1,
            "n_flipped": 0,
        }
    )
    assert report.search is None and report.coding is None


def test_summary_says_smallest_flip_found_and_prints_the_budget() -> None:
    from borges.cli_render import summary_lines
    from borges.runs.models import RunSnapshot

    result = AnalysisResult(estimate=0.1, ci_low=0, ci_high=0.2, p_value=0.01, n=5)
    report = Report(
        question="q",
        original_verdict="SHIP",
        original_result=result,
        minimal_flip=None,
        influences=[],
        robustness=1.0,
        n_universes=1,
        n_flipped=0,
        search=SearchSummary(levels_explored=1, universe_budget=9, universes_used=3),
        coding=CodingSummary(options=4, smoke_tested=4),
    )
    text = "\n".join(summary_lines(RunSnapshot(run_id="r", status="completed", report=report)))
    assert "Smallest flip found: none" in text and "Minimal flip" not in text
    assert "Search budget: 3 of 9 universes used" in text
    assert "Coding: 4 options written" in text
