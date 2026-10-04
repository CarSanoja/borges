from __future__ import annotations

from borges.analysis.models import AnalysisResult, StepTrace
from borges.garden.models import Garden, Universe
from borges.garden.outcome_scale import mentions_log_scale, scale_note


def garden(scale: dict[str, str] | None, estimate: float = 0.0293) -> Garden:
    design = {"model": "OLS"} if scale is None else {"model": "OLS", "outcome_log": scale}
    trace = StepTrace(step_id="m", option_id="o", rows_before=10, rows_after=10, design=design)
    result = AnalysisResult(estimate=estimate, ci_low=-0.05, ci_high=0.11, p_value=0.47, n=93)
    baseline = Universe(
        id="u0", choices={}, kind="baseline", status="done", result=result, traces=[trace]
    )
    return Garden(baseline_id="u0", universes={"u0": baseline})


def test_a_log1p_outcome_is_described_as_a_percentage() -> None:
    note = scale_note(garden({"kind": "log1p", "column": "alldeaths"}))
    assert note is not None
    assert "a model of log1p(alldeaths)" in note and "about 3.0% more alldeaths" in note
    assert "not 0.0293 additional alldeaths" in note


def test_a_log_link_model_is_named_and_a_negative_estimate_reads_less() -> None:
    note = scale_note(garden({"kind": "log link", "column": "deaths"}, estimate=-0.2))
    assert note is not None and "a log-link model of deaths" in note and "18.1% less" in note


def test_an_estimate_on_the_metric_scale_has_no_note() -> None:
    assert scale_note(garden(None)) is None


def test_log_words_are_recognised() -> None:
    assert mentions_log_scale("a coefficient on the log scale")
    assert not mentions_log_scale("0.03 additional deaths")
