from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.estimand import estimand_detail
from borges.garden.models import Universe


def _universe(terms: list[str]) -> Universe:
    trace = StepTrace(
        step_id="model", option_id="o", rows_before=1, rows_after=1, design={"terms": terms}
    )
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
