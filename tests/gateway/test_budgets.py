from __future__ import annotations

import asyncio

import pytest

from borges.config import Settings
from borges.gateway.budgets import BudgetBook
from borges.gateway.errors import GatewayBudgetExceeded
from borges.gateway.policy_load import policy_for
from borges.llm.client import BudgetExceeded


def book(settings: Settings, **agent: object) -> BudgetBook:
    loaded = policy_for(settings)
    policy = loaded.policy.model_copy(deep=True)
    policy.agents["judge"] = policy.agents["judge"].model_copy(update=agent)
    return BudgetBook(policy)


def test_calls_are_limited_per_agent(settings: Settings) -> None:
    budgets = book(settings, max_calls_per_run=2)
    budgets.reserve("judge", 0.0)
    budgets.reserve("judge", 0.0)
    with pytest.raises(GatewayBudgetExceeded, match="agent judge reached its limit of 2 calls"):
        budgets.reserve("judge", 0.0)
    budgets.reserve("coder", 0.0)


def test_other_agents_keep_their_own_allowance(settings: Settings) -> None:
    budgets = book(settings, max_calls_per_run=1)
    budgets.reserve("judge", 0.0)
    with pytest.raises(GatewayBudgetExceeded):
        budgets.reserve("judge", 0.0)
    assert budgets.reserve("planner", 0.0).agent_id == "planner"


def test_cost_is_reserved_before_the_call(settings: Settings) -> None:
    budgets = book(settings, max_cost_usd_per_run=0.10)
    first = budgets.reserve("judge", 0.06)
    with pytest.raises(GatewayBudgetExceeded, match="cost limit"):
        budgets.reserve("judge", 0.06)
    budgets.settle(first, 0.01)
    budgets.reserve("judge", 0.06)
    assert budgets.snapshot()["judge"]["spent_usd"] == 0.01


def test_release_returns_the_reservation(settings: Settings) -> None:
    budgets = book(settings, max_cost_usd_per_run=0.10)
    held = budgets.reserve("judge", 0.09)
    budgets.release(held)
    assert budgets.snapshot()["judge"]["reserved_usd"] == 0.0
    budgets.reserve("judge", 0.09)


def test_run_cost_cap_applies_across_agents(settings: Settings) -> None:
    loaded = policy_for(settings)
    policy = loaded.policy.model_copy(deep=True)
    policy.run = policy.run.model_copy(update={"max_cost_usd": 0.05})
    budgets = BudgetBook(policy)
    budgets.reserve("judge", 0.03)
    with pytest.raises(GatewayBudgetExceeded, match="run would pass"):
        budgets.reserve("coder", 0.03)


def test_budget_denial_is_a_budget_exceeded_for_existing_handlers(settings: Settings) -> None:
    budgets = book(settings, max_calls_per_run=1)
    budgets.reserve("judge", 0.0)
    with pytest.raises(BudgetExceeded):
        budgets.reserve("judge", 0.0)


def test_sandbox_executions_are_counted(settings: Settings) -> None:
    loaded = policy_for(settings)
    policy = loaded.policy.model_copy(deep=True)
    policy.run = policy.run.model_copy(update={"max_sandbox_execs": 2})
    budgets = BudgetBook(policy)
    budgets.reserve_exec()
    budgets.reserve_exec()
    with pytest.raises(GatewayBudgetExceeded, match="sandbox executions"):
        budgets.reserve_exec()


async def test_concurrency_slot_caps_in_flight_calls(settings: Settings) -> None:
    budgets = book(settings, max_concurrent_calls=2)
    active = peak = 0

    async def work() -> None:
        nonlocal active, peak
        async with budgets.slot("judge"):
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(*(work() for _ in range(8)))
    assert peak == 2
