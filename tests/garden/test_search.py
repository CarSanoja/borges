from __future__ import annotations

import pytest

from borges.garden.executor import universe_id
from borges.garden.models import Garden
from borges.garden.search import (
    changes_for,
    combination_flip_choices,
    minimal_flip,
    single_flip_choices,
)
from tests.garden.fakes import FakeBackend, build_garden, install_fake_harness, make_plan


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


def test_changes_for_describes_each_deviation_in_step_order() -> None:
    plan = make_plan()
    changes = changes_for(plan, {"s1": "a", "s2": "y", "s3": "n"})
    assert [c.step_id for c in changes] == ["s2", "s3"]
    assert changes[0].from_option == "x" and changes[0].to_option == "y"
    assert changes[0].to_label == "label y" and changes[0].rationale == "why y"
    assert changes[0].source == "src" and changes[0].defensibility == 0.5
    assert changes_for(plan, plan.default_choices()) == []


def test_single_flip_choices_cover_every_non_default_option() -> None:
    plan = make_plan()
    base = plan.default_choices()
    assert single_flip_choices(plan) == [
        {**base, "s1": "b"},
        {**base, "s2": "y"},
        {**base, "s3": "n"},
        {**base, "s3": "o"},
    ]


async def test_combination_pairs_rank_by_movement() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    base = plan.default_choices()
    pairs = combination_flip_choices(plan, garden, 2, 10)
    assert len(pairs) == 5
    assert pairs[0] == {**base, "s2": "y", "s3": "o"}
    assert pairs[-1] == {**base, "s1": "b", "s3": "n"}
    assert all(len([k for k in p if p[k] != base[k]]) == 2 for p in pairs)
    assert len(combination_flip_choices(plan, garden, 2, 2)) == 2
    assert combination_flip_choices(plan, garden, 2, 0) == []


async def test_combination_choices_skip_universes_already_in_garden() -> None:
    plan = make_plan()
    executor, garden = await build_garden(plan, FakeBackend(plan))
    top = combination_flip_choices(plan, garden, 2, 1)[0]
    garden.add(await executor.run_universe(top, "combination"))
    remaining = combination_flip_choices(plan, garden, 2, 10)
    assert top not in remaining
    assert universe_id(top) in garden.universes
    assert len(remaining) == 4


def test_combination_choices_without_baseline_are_empty() -> None:
    assert combination_flip_choices(make_plan(), Garden(), 2, 5) == []


async def test_combination_choices_below_size_two_are_empty() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    assert combination_flip_choices(plan, garden, 1, 5) == []


async def test_combination_triples_extend_finished_pairs_with_one_more_step() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan), with_pairs=True)
    base = plan.default_choices()
    triples = combination_flip_choices(plan, garden, 3, 10)
    assert triples
    assert all(sum(t[k] != base[k] for k in t) == 3 for t in triples)
    assert all(universe_id(t) not in garden.universes for t in triples)
    assert len({universe_id(t) for t in triples}) == len(triples)


async def test_minimal_flip_prefers_fewest_changes_then_defensibility_then_move() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan), with_pairs=True)
    flip = minimal_flip(plan, garden)
    assert flip is not None
    assert [c.step_id for c in flip.changes] == ["s3"]
    assert flip.changes[0].to_option == "o"
    assert flip.baseline_verdict == "SHIP" and flip.flipped_verdict == "DON'T SHIP"
    assert flip.baseline_result.estimate == pytest.approx(1.0)
    assert flip.flipped_result.estimate == pytest.approx(-1.1)
    assert flip.kind == "direction"


async def test_minimal_flip_tiebreak_on_defensibility_and_move() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    flip = minimal_flip(plan, garden)
    assert flip is not None
    assert flip.changes[0].defensibility == 0.9
    plan.step("s3").option("o").defensibility = 0.4
    flip = minimal_flip(plan, garden)
    assert flip is not None
    assert (flip.changes[0].step_id, flip.changes[0].to_option) == ("s2", "y")
    plan.step("s2").option("y").defensibility = 0.4
    flip = minimal_flip(plan, garden)
    assert flip is not None
    assert (flip.changes[0].step_id, flip.changes[0].to_option) == ("s3", "o")


async def test_minimal_flip_treats_missing_defensibility_as_high() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    plan.step("s3").option("o").defensibility = 0.85
    plan.step("s2").option("y").defensibility = None
    flip = minimal_flip(plan, garden)
    assert flip is not None
    assert flip.changes[0].step_id == "s2"


async def test_minimal_flip_none_when_nothing_flips() -> None:
    plan = make_plan()
    _, garden = await build_garden(plan, FakeBackend(plan))
    for universe in garden.universes.values():
        universe.flipped = False
    assert minimal_flip(plan, garden) is None
