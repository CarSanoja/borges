from __future__ import annotations

from collections import Counter

from borges.garden.models import NoopOption
from borges.garden.sampling import (
    MIN_SAMPLE,
    SAMPLE_DRAWS,
    affordable_prefix,
    choice_key,
    draw_grid,
    full_grid,
    grid_draws,
    grid_options,
    sampled_ids,
    seed_for,
)
from tests.garden.synthetic import garden_of, option, plan_of, result, step_of, universe


def plan():
    return plan_of(
        step_of("a", "filter", option("a0", True), option("a1"), option("a2")),
        step_of("m", "model", option("m0", True), option("m1")),
    )


def test_grid_options_leave_out_noop_options() -> None:
    noops = [NoopOption(step_id="a", option_id="a2", label="l", reason="r")]
    assert grid_options(plan(), noops) == {"a": ["a0", "a1"], "m": ["m0", "m1"]}


def test_draws_are_deterministic_and_cover_every_option_uniformly() -> None:
    first = draw_grid(plan(), [], 600)
    assert first == draw_grid(plan(), [], 600)
    counts = Counter(d["a"] for d in first)
    assert set(counts) == {"a0", "a1", "a2"}
    assert all(150 < n < 250 for n in counts.values())
    assert len(draw_grid(plan(), [])) == SAMPLE_DRAWS


def test_draws_never_use_a_noop_option() -> None:
    noops = [NoopOption(step_id="a", option_id="a2", label="l", reason="r")]
    assert all(d["a"] != "a2" for d in draw_grid(plan(), noops, 200))


def test_affordable_prefix_cuts_at_the_first_draw_that_does_not_fit() -> None:
    p = plan()
    garden = garden_of(p, universe(p, {}, result(1.0)))
    base = p.default_choices()
    draws = [
        {**base, "a": "a1"},
        {**base, "a": "a1"},
        {**base, "m": "m1"},
        {**base, "a": "a2"},
        {**base, "a": "a1", "m": "m1"},
    ]
    kept, new = affordable_prefix(draws, garden, 2)
    assert kept == draws[:3]
    assert new == [draws[0], draws[2]]
    kept_all, _ = affordable_prefix(draws, garden, 10)
    assert kept_all == draws


def test_draws_already_explored_cost_nothing() -> None:
    p = plan()
    garden = garden_of(p, universe(p, {}, result(1.0)), universe(p, {"a": "a1"}, result(0.9)))
    draws = [{**p.default_choices(), "a": "a1"}] * 3 + [p.default_choices()] * 2
    kept, new = affordable_prefix(draws, garden, 0)
    assert kept == draws and new == []
    ids = sampled_ids(garden, kept)
    assert len(ids) == 5 and len(set(ids)) == 2


def test_the_sample_needs_a_minimum_of_draws_to_count() -> None:
    assert MIN_SAMPLE < SAMPLE_DRAWS


def test_the_whole_grid_is_enumerated_when_it_fits_the_budget() -> None:
    p = plan()
    garden = garden_of(p, universe(p, {}, result(1.0)))
    kept, new, kind = grid_draws(p, [], garden, 10, seed_for("r_1"))
    assert kind == "grid" and len(kept) == 6 and len(new) == 5
    assert {choice_key(c) for c in kept} == {choice_key(c) for c in full_grid(p, [])}


def test_a_grid_larger_than_the_budget_is_sampled_with_the_run_seed() -> None:
    p = plan()
    garden = garden_of(p, universe(p, {}, result(1.0)))
    kept, new, kind = grid_draws(p, [], garden, 2, seed_for("r_1"))
    assert kind == "sample" and len(new) <= 2
    assert kept == affordable_prefix(draw_grid(p, [], seed=seed_for("r_1")), garden, 2)[0]
    assert seed_for("r_1") != seed_for("r_2")
