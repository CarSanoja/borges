from __future__ import annotations

import asyncio

import pytest

from borges.gateway.breaker import BreakerState
from borges.gateway.errors import GatewayBudgetExceeded
from borges.gateway.policy_load import policy_for
from borges.llm.client import Role

from .conftest import FakeLLM
from .test_llm_route import Status, ask, tweak


async def test_every_retry_counts_against_the_call_cap(make_gateway, settings) -> None:
    gateway = make_gateway(loaded=tweak(policy_for(settings), "judge", max_calls_per_run=2))
    llm = FakeLLM([Status(503)] * 5)
    with pytest.raises(GatewayBudgetExceeded):
        await ask(gateway, llm, Role.JUDGE)
    assert len(llm.calls) == 2
    snapshot = gateway.budgets.snapshot()
    assert snapshot["judge"]["calls"] == 2 and snapshot["judge"]["reserved_usd"] == 0.0


async def test_retries_cannot_push_spend_past_the_cost_cap(make_gateway, settings) -> None:
    gateway = make_gateway(loaded=tweak(policy_for(settings), "judge", max_cost_usd_per_run=0.0))
    llm = FakeLLM([Status(503)] * 5)
    with pytest.raises(GatewayBudgetExceeded):
        await ask(gateway, llm, Role.JUDGE)
    assert not llm.calls


async def test_a_cancelled_call_releases_its_reservation(make_gateway) -> None:
    gateway = make_gateway()
    llm = FakeLLM([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await ask(gateway, llm, Role.JUDGE)
    assert gateway.budgets.snapshot()["judge"]["reserved_usd"] == 0.0
    assert gateway.budgets.snapshot()["run"]["reserved_usd"] == 0.0


async def test_a_cancelled_probe_does_not_wedge_the_breaker(make_gateway, clock) -> None:
    gateway = make_gateway()
    model = "nvidia/nemotron-3-super-120b-a12b"
    await _open_breaker(gateway)
    assert gateway.breakers.of(model).state is BreakerState.OPEN
    clock.now += 31
    with pytest.raises(asyncio.CancelledError):
        await ask(gateway, FakeLLM([asyncio.CancelledError()]), Role.JUDGE)
    assert gateway.breakers.of(model).allow()


async def test_a_non_transient_probe_failure_does_not_wedge_the_breaker(
    make_gateway, clock
) -> None:
    gateway = make_gateway()
    model = "nvidia/nemotron-3-super-120b-a12b"
    await _open_breaker(gateway)
    clock.now += 31
    with pytest.raises(Status):
        await ask(gateway, FakeLLM([Status(400)]), Role.JUDGE)
    assert gateway.breakers.of(model).allow()


async def _open_breaker(gateway) -> None:
    llm = FakeLLM([Status(503)] * 8)
    for _ in range(2):
        with pytest.raises(Status):
            await ask(gateway, llm, Role.JUDGE)
