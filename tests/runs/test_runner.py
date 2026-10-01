from __future__ import annotations

import asyncio
from typing import Any

import pytest

from borges.garden.models import Garden, Universe
from borges.llm.client import BudgetExceeded
from borges.runs.runner import UniverseRunner
from tests.runs.fakes import make_plan


class Executor:
    def __init__(self) -> None:
        self.cancelled: list[str] = []
        self.completed: list[str] = []

    async def run_universe(self, choices: dict[str, str], kind: str) -> Universe:
        name = ",".join(sorted(choices.values()))
        if choices.get("s1") == "b":
            await asyncio.sleep(0.01)
            raise BudgetExceeded("cap")
        try:
            await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            self.cancelled.append(name)
            raise
        self.completed.append(name)
        return Universe(id=f"u_{name}", choices=choices, changed=[], kind=kind, status="done")


async def test_run_many_failure_cancels_in_flight_siblings() -> None:
    plan = make_plan()
    executor = Executor()
    runner = UniverseRunner(None, plan, executor, Garden(), None, 10)
    defaults: dict[str, Any] = plan.default_choices()
    choices = [{**defaults, "s2": "y"}, {**defaults, "s1": "b"}, {**defaults, "s2": "adv"}]
    with pytest.raises(BudgetExceeded):
        await runner.run_many(choices, "single")
    await asyncio.sleep(0.4)
    assert len(executor.cancelled) == 2
    assert executor.completed == []
