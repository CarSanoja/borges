from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.aliased import aliased_caveats
from borges.garden.models import Garden, Universe


def universe(uid: str, note: str) -> Universe:
    trace = StepTrace(step_id="m", option_id="o", rows_before=9, rows_after=9, note=note)
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
