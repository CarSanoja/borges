from __future__ import annotations

import re

from borges.garden.report_notes import figure_caveats
from borges.garden.robustness import RobustnessFigures
from tests.garden.synthetic import option, plan_of, step_of

PLAN = plan_of(step_of("m", "model", option("a", True), option("b")))
NOTE = "uniform random sample of the grid: 12 draws, 10 distinct results"


def figures(**extra) -> RobustnessFigures:
    base = dict(
        headline=0.56,
        basis="design_weighted",
        beam=0.67,
        design=0.56,
        design_note=NOTE,
        low=0.3,
        high=0.79,
        n_distinct=15,
        rating=0.56,
        rating_reason=None,
    )
    return RobustnessFigures(**{**base, **extra})


def sampling_note(**extra) -> str:
    notes = figure_caveats(PLAN, 15, figures(**extra), [], None, [])
    return next(n for n in notes if "robustness estimate" in n)


def test_the_caveat_is_not_called_a_headline_and_names_the_grid_share_once() -> None:
    note = sampling_note()
    assert "headline" not in note.lower()
    assert "56% robustness estimate is the share of the analysis grid" in note
    assert NOTE in note


def test_the_caveat_carries_no_second_competing_percentage() -> None:
    note = sampling_note()
    assert re.findall(r"\d+%", note) == ["56%"]
    assert "67%" not in note
    assert "leans toward flips" in note


def test_the_failed_tail_still_follows_the_estimate() -> None:
    notes = figure_caveats(PLAN, 15, figures(), [], None, [], n_failed=2)
    note = next(n for n in notes if "robustness estimate" in n)
    assert "15 of 17 attempted completed" in note
