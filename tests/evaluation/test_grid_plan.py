from __future__ import annotations

from pathlib import Path

import pytest

from borges.evaluation.grid_plan import (
    enumerate_grid,
    grid_size,
    load_events,
    sample_grid,
    seeded_plan,
)
from tests.evaluation.grid_support import small_plan

CASES = Path(__file__).resolve().parents[2] / "cases"
EXPECTED = {"red_cards": 72, "checkout_ab": 32, "marp_norms": 1536, "marp_religiosity": 768}


def test_enumeration_is_the_full_cartesian_product_with_the_baseline_first() -> None:
    plan, _ = small_plan()
    universes = enumerate_grid(plan)
    assert len(universes) == grid_size(plan) == 4
    assert universes[0] == plan.default_choices()
    assert len({tuple(sorted(u.items())) for u in universes}) == 4


def test_cap_keeps_the_baseline_and_is_deterministic_by_seed() -> None:
    plan, _ = small_plan()
    universes = enumerate_grid(plan)
    first = sample_grid(universes, plan, 3, seed=1)
    assert len(first) == 3 and first[0] == plan.default_choices()
    assert first == sample_grid(universes, plan, 3, seed=1)
    assert any(first != sample_grid(universes, plan, 3, seed=s) for s in range(2, 12))
    assert sample_grid(universes, plan, 4, seed=1) == universes
    assert sample_grid(universes, plan, None, seed=1) == universes


@pytest.mark.parametrize("case_id,size", sorted(EXPECTED.items()))
def test_recorded_seeded_plans_have_the_documented_grid_size(case_id: str, size: int) -> None:
    events = load_events(CASES / case_id / "recorded" / "events.jsonl")
    plan = seeded_plan(events)
    assert grid_size(plan) == size
    assert all(o.origin != "adversary" and o.code for s in plan.steps for o in s.options)
    assert len(enumerate_grid(plan)) == size


def test_seeded_plan_refuses_a_recording_without_a_coded_plan() -> None:
    with pytest.raises(ValueError):
        seeded_plan([{"type": "run.started", "data": {}}])
