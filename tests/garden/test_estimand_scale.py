from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.estimand import estimand_detail
from borges.garden.models import Universe


def universe(scale: dict[str, str] | None, terms: tuple[str, ...] = ("x",)) -> Universe:
    design: dict[str, object] = {"terms": list(terms)}
    if scale is not None:
        design["outcome_log"] = scale
    trace = StepTrace(step_id="m", option_id="o", rows_before=9, rows_after=9, design=design)
    return Universe(id="u", choices={}, kind="single", status="done", traces=[trace])


LOG1P = {"kind": "log1p", "column": "alldeaths"}


def test_a_log_outcome_against_a_raw_one_is_an_estimand_change() -> None:
    detail = estimand_detail(universe(None), universe(LOG1P))
    assert detail is not None
    assert detail.startswith(
        "puts the outcome on another scale (log1p(alldeaths) instead of alldeaths)"
    )


def test_a_log_link_against_a_log1p_outcome_is_named_both_ways() -> None:
    detail = estimand_detail(universe(LOG1P), universe({"kind": "log link", "column": "alldeaths"}))
    assert detail is not None and "(a log-link model of alldeaths instead of log1p(alldeaths))" in (
        detail
    )


def test_the_same_scale_falls_through_to_the_covariate_check() -> None:
    assert estimand_detail(universe(LOG1P), universe(LOG1P)) is None
    changed = estimand_detail(universe(LOG1P), universe(LOG1P, ("x", "wind")))
    assert changed is not None and changed.startswith("changes the covariates of the model")
