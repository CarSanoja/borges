from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.aliased import aliased_caveats, tangled_caveats
from borges.garden.models import Garden, Universe


def universe(uid: str, note: str, names: list[str] | None = None) -> Universe:
    design = {"names": names} if names else None
    trace = StepTrace(
        step_id="m", option_id="o", rows_before=9, rows_after=9, note=note, design=design
    )
    return Universe(id=uid, choices={}, kind="single", traces=[trace])


def test_no_aliased_covariates_means_no_caveat() -> None:
    garden = Garden()
    garden.add(universe("u1", ""))
    assert aliased_caveats(garden) == []


def test_aliased_covariates_are_counted_by_universe_and_named_once() -> None:
    garden = Garden()
    garden.add(universe("u1", "aliased covariates dropped: elapsedyrs"))
    garden.add(universe("u2", "aliased covariates dropped: elapsedyrs, region_b"))
    garden.add(universe("u3", ""))
    [caveat] = aliased_caveats(garden)
    assert caveat.startswith("In 2 universes")
    assert "(elapsedyrs, region_b)" in caveat


def test_covariates_that_rebuild_the_exposure_get_their_own_caveat() -> None:
    garden = Garden()
    garden.add(
        universe(
            "u1",
            "aliased covariates dropped: rater2; "
            "covariates that rebuild the exposure with them dropped: rater1",
        )
    )
    [aliased] = aliased_caveats(garden)
    [tangled] = tangled_caveats(garden)
    assert "(rater2)" in aliased and "rater1" not in aliased
    assert tangled.startswith("In 1 universes the covariates rater1 were also dropped")


def test_a_covariate_put_in_the_design_twice_is_named_as_a_second_copy() -> None:
    garden = Garden()
    names = ["const", "product", "age", "age", "ses", "region_b"]
    garden.add(universe("u1", "aliased covariates dropped: age, region_b", names))
    repeated, combined = aliased_caveats(garden)
    assert "put age in its design twice" in repeated and "adjusted for once" in repeated
    assert "(region_b)" in combined and "age" not in combined
