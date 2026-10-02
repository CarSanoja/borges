from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from borges.gateway.errors import GatewayBudgetExceeded
from borges.gateway.policy_models import GatewayPolicy

RUN = "run"
SANDBOX = "sandbox"


@dataclass
class Account:
    max_calls: int
    max_cost_usd: float
    max_concurrent: int
    calls: int = 0
    spent: float = 0.0
    reserved: float = 0.0
    slots: asyncio.Semaphore = field(init=False)

    def __post_init__(self) -> None:
        self.slots = asyncio.Semaphore(self.max_concurrent)


@dataclass
class Reservation:
    agent_id: str
    estimate: float


class BudgetBook:
    """Reserves calls and spend per agent and per run before a call, settles after."""

    def __init__(self, policy: GatewayPolicy) -> None:
        run = policy.run
        self._accounts: dict[str, Account] = {
            RUN: Account(run.max_calls, run.max_cost_usd, run.max_concurrent_calls),
            SANDBOX: Account(run.max_sandbox_execs, float("inf"), run.max_concurrent_sandbox_execs),
        }
        for agent_id, agent in policy.agents.items():
            self._accounts[agent_id] = Account(
                agent.max_calls_per_run, agent.max_cost_usd_per_run, agent.max_concurrent_calls
            )

    def account(self, name: str) -> Account:
        return self._accounts[name]

    def reserve(self, agent_id: str, estimate: float, count_call: bool = True) -> Reservation:
        accounts = [self._accounts[agent_id], self._accounts[RUN]]
        for account, label in zip(accounts, (f"agent {agent_id}", "run"), strict=True):
            if count_call and account.calls + 1 > account.max_calls:
                raise GatewayBudgetExceeded(
                    "budget", f"{label} reached its limit of {account.max_calls} calls", agent_id
                )
            projected = account.spent + account.reserved + estimate
            if projected > account.max_cost_usd:
                raise GatewayBudgetExceeded(
                    "budget",
                    f"{label} would pass its cost limit of ${account.max_cost_usd:.2f} "
                    f"(spent ${account.spent:.4f}, this call ~${estimate:.4f})",
                    agent_id,
                )
        for account in accounts:
            account.calls += int(count_call)
            account.reserved += estimate
        return Reservation(agent_id, estimate)

    def settle(self, reservation: Reservation, actual: float) -> None:
        for name in (reservation.agent_id, RUN):
            account = self._accounts[name]
            account.reserved = max(0.0, account.reserved - reservation.estimate)
            account.spent += actual

    def release(self, reservation: Reservation) -> None:
        self.settle(reservation, 0.0)

    def reserve_exec(self) -> None:
        account = self._accounts[SANDBOX]
        if account.calls + 1 > account.max_calls:
            raise GatewayBudgetExceeded(
                "budget", f"run reached its limit of {account.max_calls} sandbox executions"
            )
        account.calls += 1

    @asynccontextmanager
    async def slot(self, agent_id: str) -> AsyncIterator[None]:
        async with self._accounts[RUN].slots, self._accounts[agent_id].slots:
            yield

    @asynccontextmanager
    async def exec_slot(self) -> AsyncIterator[None]:
        async with self._accounts[SANDBOX].slots:
            yield

    def snapshot(self) -> dict[str, dict[str, float]]:
        return {
            name: {
                "calls": a.calls,
                "spent_usd": round(a.spent, 6),
                "reserved_usd": round(a.reserved, 6),
            }
            for name, a in self._accounts.items()
        }
