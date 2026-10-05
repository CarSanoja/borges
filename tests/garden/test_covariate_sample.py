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
