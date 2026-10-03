from __future__ import annotations

import pytest

from borges.garden.models import NoopOption
from borges.garden.robustness import (
    MIN_DISTINCT_TO_RATE,
    distinct_universes,
    robustness_figures,
)
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe

SHIP = result(1.0)
STOP = result(0.0, half=0.2, p=0.9)


def two_decision_plan():
    return plan_of(
        step_of("a", "filter", option("a0", True), option("a1"), option("a2")),
        step_of("m", "model", option("m0", True), option("m1")),
    )


def test_identical_results_are_counted_once() -> None:
    plan = two_decision_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, SHIP),
        universe(plan, {"a": "a1"}, result(0.9)),
        universe(plan, {"a": "a2"}, result(0.9)),
        universe(plan, {"m": "m1"}, STOP),
    )
    figures = robustness_figures(plan, garden, [])
    assert len(garden.finished()) == 4
    assert figures.n_distinct == 3
    assert figures.beam == pytest.approx(2 / 3)
    assert len(distinct_universes(garden.finished())) == 3


def test_noop_universes_are_left_out_of_the_share() -> None:
    plan = two_decision_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, SHIP),
        universe(plan, {"a": "a1"}, SHIP),
        universe(plan, {"m": "m1"}, STOP),
    )
    noop = [NoopOption(step_id="a", option_id="a1", label="l", reason="r")]
    with_noop = robustness_figures(plan, garden, [])
    without = robustness_figures(plan, garden, noop)
    assert with_noop.n_distinct == without.n_distinct == 2
    assert without.beam == pytest.approx(0.5)
    assert without.design == pytest.approx(0.5)


def test_design_weighted_share_is_the_headline_and_the_beam_share_is_reported() -> None:
    plan = two_decision_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, SHIP),
        universe(plan, {"a": "a1"}, result(0.8)),
        universe(plan, {"a": "a2"}, result(0.7)),
        universe(plan, {"m": "m1"}, STOP),
        universe(plan, {"a": "a1", "m": "m1"}, result(-0.1, p=0.8)),
        universe(plan, {"a": "a2", "m": "m1"}, result(-0.2, p=0.8)),
    )
    figures = robustness_figures(plan, garden, [])
    assert figures.beam == pytest.approx(3 / 6)
    assert figures.design == pytest.approx((1.0 + 0.5) / 2)
    assert figures.headline == figures.design
    assert figures.basis == "design_weighted"


def test_headline_falls_back_to_distinct_results_without_singles() -> None:
    plan = two_decision_plan()
    garden = garden_of(
        plan,
        universe(plan, {}, SHIP),
        universe(plan, {"a": "a1", "m": "m1"}, STOP),
    )
    figures = robustness_figures(plan, garden, [])
    assert figures.design is None
    assert figures.basis == "distinct_results" and figures.headline == pytest.approx(0.5)


def test_fewer_than_ten_distinct_universes_get_no_rating() -> None:
    plan = two_decision_plan()
    garden = garden_of(plan, universe(plan, {}, SHIP), universe(plan, {"a": "a1"}, result(0.9)))
    figures = robustness_figures(plan, garden, [])
    assert figures.rating is None
    assert figures.rating_reason == "n=2, too few to rate"


def test_ten_distinct_universes_are_rated() -> None:
    options = [option("o0", True), *(option(f"o{i}") for i in range(1, MIN_DISTINCT_TO_RATE))]
    plan = plan_of(step_of("a", "filter", *options))
    garden = garden_of(
        plan,
        universe(plan, {}, SHIP),
        *(universe(plan, {"a": f"o{i}"}, result(1.0 - i / 100)) for i in range(1, 10)),
    )
    figures = robustness_figures(plan, garden, [])
    assert figures.n_distinct == 10
    assert figures.rating == figures.headline == pytest.approx(1.0)
    assert figures.rating_reason is None


def test_a_uniform_sample_is_the_design_weighted_figure_when_it_is_large_enough() -> None:
    plan = two_decision_plan()
    flips = [
        universe(plan, {"a": "a1", "m": "m1"}, result(-0.1, p=0.8)),
        universe(plan, {"a": "a2", "m": "m1"}, result(-0.2, p=0.8)),
    ]
    stays = [
        universe(plan, {}, SHIP),
        universe(plan, {"a": "a1"}, result(0.8)),
        universe(plan, {"a": "a2"}, result(0.7)),
        universe(plan, {"m": "m1"}, result(0.6)),
    ]
    garden = garden_of(plan, *stays, *flips)
    garden.sample_ids = [u.id for u in [*stays, *flips]]
    figures = robustness_figures(plan, garden, [])
    assert figures.design == pytest.approx(4 / 6)
    assert figures.beam == pytest.approx(4 / 6)
    assert figures.design_note is not None and "uniform random sample" in figures.design_note
    assert "6 draws" in figures.design_note


def test_a_sample_below_the_minimum_falls_back_to_one_decision_at_a_time() -> None:
    plan = two_decision_plan()
    garden = garden_of(plan, universe(plan, {}, SHIP), universe(plan, {"a": "a1"}, result(0.8)))
    garden.sample_ids = [u.id for u in garden.universes.values()]
    figures = robustness_figures(plan, garden, [])
    assert (
        figures.design_note is not None and "one decision changed at a time" in figures.design_note
    )
