from __future__ import annotations

import pytest

from borges.bench.blade_cost import CostRefused, check_budget, estimate_usd


def test_estimate_scales_with_datasets_arms_and_repeats() -> None:
    one = estimate_usd(1, ["planner"], 1, False)
    assert estimate_usd(2, ["planner"], 1, False) == pytest.approx(2 * one)
    assert estimate_usd(1, ["planner"], 3, False) == pytest.approx(3 * one)
    assert estimate_usd(1, ["planner", "adversary"], 1, False) > one
    assert estimate_usd(1, ["planner"], 1, True) > one


def test_the_default_full_benchmark_is_refused_under_the_default_cap_with_repeats() -> None:
    assert estimate_usd(12, ["planner", "adversary"], 1, True) <= 2.0
    with pytest.raises(CostRefused, match="exceeds --max-usd"):
        check_budget(estimate_usd(12, ["planner", "adversary"], 3, True), 2.0)


def test_within_budget_passes() -> None:
    check_budget(0.5, 2.0)
