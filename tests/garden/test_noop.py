from __future__ import annotations

from borges.garden.noop import FINGERPRINT_REASON, RESULT_REASON, noop_options
from tests.garden.synthetic import (
    garden_of,
    option,
    plan_of,
    result,
    step_of,
    trace,
    universe,
)


def test_a_step_with_the_baseline_fingerprint_is_a_noop() -> None:
    plan = plan_of(
        step_of("rows", "filter", option("keep", True), option("zero_games")),
        step_of("model", "model", option("m", True), option("n")),
    )
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0), traces=[trace("rows", fingerprint="aa")]),
        universe(
            plan, {"rows": "zero_games"}, result(1.0), traces=[trace("rows", fingerprint="aa")]
        ),
        universe(plan, {"model": "n"}, result(0.5)),
    )
    found = noop_options(plan, garden)
    assert [(n.step_id, n.option_id, n.reason) for n in found] == [
        ("rows", "zero_games", FINGERPRINT_REASON)
    ]


def test_identical_result_to_six_digits_is_a_noop_without_fingerprints() -> None:
    plan = plan_of(step_of("model", "model", option("m", True), option("n"), option("k")))
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.3408123)),
        universe(plan, {"model": "n"}, result(1.34081234)),
        universe(plan, {"model": "k"}, result(1.35)),
    )
    found = noop_options(plan, garden)
    assert [(n.option_id, n.reason) for n in found] == [("n", RESULT_REASON)]


def test_an_option_that_matters_in_another_universe_is_not_a_noop() -> None:
    plan = plan_of(
        step_of("rows", "filter", option("keep", True), option("alt")),
        step_of("model", "model", option("m", True), option("n")),
    )
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"rows": "alt"}, result(1.0)),
        universe(plan, {"model": "n"}, result(0.5)),
        universe(plan, {"rows": "alt", "model": "n"}, result(0.1)),
    )
    assert noop_options(plan, garden) == []


def test_failed_singles_are_never_noops() -> None:
    plan = plan_of(step_of("model", "model", option("m", True), option("n")))
    broken = universe(plan, {"model": "n"}, result(1.0))
    broken.status, broken.result = "failed", None
    garden = garden_of(plan, universe(plan, {}, result(1.0)))
    garden.add(broken)
    assert noop_options(plan, garden) == []


def test_noop_options_are_excluded_from_flips_and_combinations() -> None:
    from borges.garden.search import combination_flip_choices, minimal_flip

    plan = plan_of(
        step_of("rows", "filter", option("keep", True), option("zero")),
        step_of("model", "model", option("m", True), option("n")),
        step_of("scale", "transform", option("s", True), option("t")),
    )
    garden = garden_of(
        plan,
        universe(plan, {}, result(1.0)),
        universe(plan, {"rows": "zero"}, result(1.0)),
        universe(plan, {"model": "n"}, result(0.9)),
        universe(plan, {"scale": "t"}, result(0.8)),
        universe(plan, {"rows": "zero", "model": "n"}, result(0.9)),
        universe(plan, {"rows": "zero", "scale": "t", "model": "n"}, result(-0.3, p=0.9)),
    )
    assert minimal_flip(plan, garden) is None
    pairs = combination_flip_choices(plan, garden, 2, 10)
    assert pairs and all(p["rows"] == "keep" for p in pairs)
