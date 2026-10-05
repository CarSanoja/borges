from __future__ import annotations

from borges.garden.exposure_spread import exposure_spread_notes
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, trace, universe


def scale_plan():
    return plan_of(
        step_of(
            "scale",
            "transform",
            option("mean", True, label="Mean of the items"),
            option("pca", label="First principal component"),
        ),
        step_of("model", "model", option("ols", True), option("robust")),
    )


def model_trace(sd: float, binary: bool = False):
    return trace("model", exposure="rel", exposure_sd=sd, exposure_binary=binary)


def test_options_that_build_the_exposure_on_another_scale_are_named() -> None:
    plan = scale_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, result(0.093), traces=[model_trace(0.8)]),
        universe(plan, {"model": "robust"}, result(0.093), traces=[model_trace(0.8)]),
        universe(plan, {"scale": "pca"}, result(0.045), traces=[model_trace(2.4)]),
    )
    notes = exposure_spread_notes(plan, garden)
    assert len(notes) == 1
    assert "The options of 'Step scale' build the exposure on different scales" in notes[0]
    assert "0.8 with 'Mean of the items'" in notes[0] and "2.4 with 'First principal" in notes[0]


def test_one_scale_or_a_binary_exposure_gives_no_note() -> None:
    plan = scale_plan()
    same = garden_of(
        plan,
        universe(plan, {}, result(0.093), traces=[model_trace(0.8)]),
        universe(plan, {"scale": "pca"}, result(0.09), traces=[model_trace(0.85)]),
    )
    binary = garden_of(
        plan,
        universe(plan, {}, result(0.093), traces=[model_trace(0.5, binary=True)]),
        universe(plan, {"scale": "pca"}, result(0.09), traces=[model_trace(0.2, binary=True)]),
    )
    assert exposure_spread_notes(plan, same) == []
    assert exposure_spread_notes(plan, binary) == []
