from __future__ import annotations

from borges.garden.covariate_sample import covariate_sample_caveats
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe


def covariate_plan():
    return plan_of(
        step_of(
            "cov",
            "feature",
            option("demo", True, label="Demographics"),
            option("contact", label="Prior contact history"),
            option("height", label="Add height"),
        ),
        step_of("model", "model", option("logit", True), option("robust")),
    )


def test_a_covariate_option_that_drops_most_rows_is_named() -> None:
    plan = covariate_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.88, n=45211)),
        universe(plan, {"cov": "contact"}, result(0.87, n=8252)),
        universe(plan, {"cov": "height"}, result(0.9, n=42000)),
    )
    notes = covariate_sample_caveats(plan, garden)
    assert len(notes) == 1
    assert "'Prior contact history' of the step 'Step cov' changes the sample" in notes[0]
    assert "keep 8,252 of the 45,211 rows that 'Demographics' keeps" in notes[0]


def test_a_covariate_option_without_a_default_twin_gives_no_note() -> None:
    plan = covariate_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.88, n=45211)),
        universe(plan, {"cov": "contact", "model": "robust"}, result(0.87, n=8252)),
    )
    assert covariate_sample_caveats(plan, garden) == []


def test_a_loss_under_one_other_choice_counts_and_names_it() -> None:
    plan = covariate_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.88, n=45211)),
        universe(plan, {"cov": "contact"}, result(0.91, n=45211)),
        universe(plan, {"model": "robust"}, result(0.88, n=45211)),
        universe(plan, {"cov": "contact", "model": "robust"}, result(0.87, n=8182)),
    )
    notes = covariate_sample_caveats(plan, garden)
    assert len(notes) == 1
    assert "so in 1 of its 2 universes (those with '" in notes[0]
    assert "at the step 'Step model') it keeps 8,182 of the 45,211 rows" in notes[0]


def test_a_step_that_builds_columns_names_them_instead_of_covariates() -> None:
    plan = covariate_plan()
    plan.step("cov").produces = ["high_fertility", "committed"]
    garden = garden_of(
        plan,
        universe(plan, {}, result(2.38, n=163)),
        universe(plan, {"cov": "contact"}, result(1.78, n=129)),
    )
    [note] = covariate_sample_caveats(plan, garden)
    assert "changes the sample: the columns it builds (high_fertility, committed)" in note
    assert "covariates" not in note and "keep 129 of the 163 rows" in note
