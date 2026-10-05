from __future__ import annotations

from borges.analysis.models import StepTrace
from borges.garden.models import Garden, Universe
from borges.garden.scaled_outcome import scaled_outcome_caveats


def universe(uid: str, note: str) -> Universe:
    trace = StepTrace(step_id="m", option_id="o", rows_before=9, rows_after=9, note=note)
    return Universe(id=uid, choices={}, kind="single", traces=[trace])


def test_no_scaled_outcome_means_no_caveat() -> None:
    garden = Garden()
    garden.add(universe("u1", "aliased covariates dropped: a"))
    assert scaled_outcome_caveats(garden) == []


def test_universes_that_z_score_the_outcome_are_counted() -> None:
    garden = Garden()
    garden.add(universe("u1", "outcome z-scored with the predictors: dg_index"))
    garden.add(
        universe(
            "u2", "aliased covariates dropped: a; outcome z-scored with the predictors: dg_index"
        )
    )
    garden.add(universe("u3", ""))
    [caveat] = scaled_outcome_caveats(garden)
    assert caveat.startswith("In 2 universes the model z-scores the outcome 'dg_index'")
