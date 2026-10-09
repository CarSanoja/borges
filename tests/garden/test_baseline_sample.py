from __future__ import annotations

from borges.analysis.models import ColumnProfile, RepeatedUnit
from borges.garden.covariate_sample import baseline_sample_caveats
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, trace, universe


def bank_plan():
    plan = plan_of(
        step_of("cov", "feature", option("all", True, code="ctx['covariates'] = ['poutcome']")),
        step_of("model", "model", option("logit", True)),
    )
    columns = [
        ColumnProfile(name="poutcome", dtype="str", n_missing=82, n_unique=3),
        ColumnProfile(name="contact", dtype="str", n_missing=82, n_unique=3),
    ]
    return plan.model_copy(update={"dataset": plan.dataset.model_copy(update={"columns": columns})})


def test_a_baseline_that_fits_a_small_share_of_its_rows_is_named() -> None:
    plan = bank_plan()
    baseline = universe(plan, {}, result(0.87, n=18), traces=[trace("cov"), trace("model")])
    [note] = baseline_sample_caveats(plan, garden_of(plan, baseline))
    assert note.startswith("The original analysis fits 18 of the 100 rows that reach its model")
    assert "the rows where poutcome is missing" in note


def test_a_baseline_that_keeps_most_rows_gives_no_note() -> None:
    plan = bank_plan()
    baseline = universe(plan, {}, result(0.87, n=85), traces=[trace("cov"), trace("model")])
    assert baseline_sample_caveats(plan, garden_of(plan, baseline)) == []


def test_a_baseline_that_fits_one_row_per_unit_names_the_unit() -> None:
    plan = bank_plan()
    unit = RepeatedUnit(name="user_id", n_units=18, rows_per_unit=5.5)
    plan.dataset = plan.dataset.model_copy(update={"repeated_units": [unit]})
    baseline = universe(plan, {}, result(0.87, n=18), traces=[trace("cov"), trace("model")])
    assert baseline_sample_caveats(plan, garden_of(plan, baseline)) == [
        "The original analysis fits one row per user_id (18 rows from the 100 that reach its "
        "model), so its unit of analysis is user_id."
    ]
