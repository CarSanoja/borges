from __future__ import annotations

from borges.analysis.models import AnalysisResult
from borges.cli_render import result_line


def test_underflowed_p_value_is_shown_as_a_bound() -> None:
    result = AnalysisResult(estimate=0.88, ci_low=0.86, ci_high=0.89, p_value=0.0, n=45211)
    assert "p < 1e-16" in result_line(result)


def test_ordinary_p_value_is_shown_exactly() -> None:
    result = AnalysisResult(estimate=1.2, ci_low=1.1, ci_high=1.3, p_value=0.0003772, n=10)
    assert "p = 0.0003772" in result_line(result)
