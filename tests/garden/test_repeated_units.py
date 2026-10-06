from __future__ import annotations

from borges.analysis.models import AnalysisResult, RepeatedUnit, StepTrace
from borges.garden.models import Garden, Universe
from borges.garden.repeated_units import repeated_unit_caveats
from tests.analysis.fakes import make_plan

RESULT = AnalysisResult(estimate=1.2, ci_low=1.0, ci_high=1.4, p_value=0.03, n=100)


def garden_with(cov_type: str | None, status: str = "done") -> Garden:
    design = None if cov_type is None else {"model": "Logit", "cov_type": cov_type}
    trace = StepTrace(step_id="m1", option_id="ols", rows_before=1, rows_after=1, design=design)
    garden = Garden(baseline_id="u0")
    garden.add(
        Universe(
            id="u0",
            choices={"m1": "ols"},
            kind="baseline",
            status=status,
            result=RESULT,
            traces=[trace],
        )
    )
    return garden


def plan_with_unit():
    plan = make_plan()
    unit = RepeatedUnit(name="playerShort", n_units=1585, rows_per_unit=78.6)
    plan.dataset = plan.dataset.model_copy(update={"repeated_units": [unit]})
    return plan


def test_an_unclustered_original_gets_the_caveat() -> None:
    assert repeated_unit_caveats(plan_with_unit(), garden_with("HC3")) == [
        "rows repeat 1,585 playerShort values; "
        "errors not clustered by playerShort may be too narrow"
    ]


def test_a_baseline_without_a_recorded_design_is_not_known_to_be_clustered() -> None:
    assert len(repeated_unit_caveats(plan_with_unit(), garden_with(None))) == 1


def test_a_clustered_original_gets_no_caveat() -> None:
    assert repeated_unit_caveats(plan_with_unit(), garden_with("cluster")) == []


def test_no_repeated_units_and_no_finished_baseline_get_no_caveat() -> None:
    assert repeated_unit_caveats(make_plan(), garden_with("HC3")) == []
    assert repeated_unit_caveats(plan_with_unit(), garden_with("HC3", "failed")) == []
    assert repeated_unit_caveats(plan_with_unit(), Garden()) == []
