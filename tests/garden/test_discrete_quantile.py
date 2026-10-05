from __future__ import annotations

from borges.analysis.models import AnalysisResult, StepTrace
from borges.garden.discrete_quantile import discrete_quantile_caveats
from borges.garden.models import Garden, Universe


def _universe(uid: str, model: str, levels: int | None, estimate: float) -> Universe:
    design = {"model": model, "endog_levels": levels}
    trace = StepTrace(step_id="m", option_id="o", rows_before=10, rows_after=10, design=design)
    result = AnalysisResult(estimate=estimate, ci_low=-1.0, ci_high=1.0, p_value=0.5, n=10)
    return Universe(id=uid, choices={}, kind="single", status="done", traces=[trace], result=result)


def test_a_median_regression_of_a_nine_level_outcome_is_named_with_the_flip() -> None:
    garden = Garden(
        universes={
            "u1": _universe("u1", "QuantReg", 9, 7.3e-07),
            "u2": _universe("u2", "QuantReg", 122, 0.066),
            "u3": _universe("u3", "OLS", 9, 0.09),
        }
    )
    [caveat] = discrete_quantile_caveats(garden, "u1")
    assert caveat.startswith("1 universe fits a quantile regression to an outcome with only 9")
    assert "it is the minimal flip" in caveat and "7.3e-07" in caveat


def test_quantiles_of_a_fine_outcome_or_other_models_say_nothing() -> None:
    garden = Garden(universes={"u2": _universe("u2", "QuantReg", 122, 0.066)})
    assert discrete_quantile_caveats(garden, None) == []
    assert (
        discrete_quantile_caveats(Garden(universes={"u": _universe("u", "OLS", 3, 0.1)}), None)
        == []
    )
