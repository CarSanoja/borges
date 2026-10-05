from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.estimand import estimand_detail
from borges.garden.models import Universe


def _universe(terms: list[str], columns: int | None = None) -> Universe:
    design: dict[str, object] = {"terms": terms}
    if columns is not None:
        design["columns"] = columns
    trace = StepTrace(step_id="model", option_id="o", rows_before=1, rows_after=1, design=design)
    return Universe(id="u", choices={}, kind="single", traces=[trace])


def test_generic_terms_with_equal_count_say_nothing() -> None:
    before = _universe(["const", "x1", "x2", "x3"])
    after = _universe(["const", "category", "masfem", "year"])
    assert estimand_detail(before, after) is None
    assert estimand_detail(_universe(["x1", "x2"]), _universe(["x1", "x2"])) is None


def test_generic_terms_with_different_count_report_numbers() -> None:
    detail = estimand_detail(_universe(["const", "x1", "x2"]), _universe(["const", "a", "b", "c"]))
    assert detail is not None
    assert "from 3 to 4" in detail
    assert "unnamed" not in detail


def test_named_terms_still_report_names() -> None:
    detail = estimand_detail(_universe(["const", "a", "b"]), _universe(["const", "a", "c"]))
    assert detail is not None and "adds c" in detail and "removes b" in detail


def test_one_derived_variable_named_differently_is_not_a_covariate_change() -> None:
    before = _universe(["age", "gender", "relig_z"])
    after = _universe(["age", "gender", "religiosity_z"])
    columns = {"age", "gender", "rel_1"}
    assert estimand_detail(before, after, columns) is None
    swapped = estimand_detail(
        _universe(["age", "age_sq"]), _universe(["age", "income_log"]), columns
    )
    assert swapped is not None and "adds income_log" in swapped
    dropped = estimand_detail(_universe(["age", "relig_z"]), _universe(["relig_z"]), columns)
    assert dropped is not None and "removes age" in dropped


def test_generic_terms_on_a_design_of_the_same_width_are_the_same_covariates() -> None:
    ols = _universe(["age", "education", "gender", "ses"], columns=7)
    quantile = _universe(["x2", "x3", "x4", "x5", "x6"], columns=7)
    assert estimand_detail(ols, quantile) is None
    wider = estimand_detail(ols, _universe(["x2", "x3", "x4", "x5", "x6", "x7", "x8"], columns=9))
    assert wider is not None and "number of columns of the model from 7 to 9" in wider
