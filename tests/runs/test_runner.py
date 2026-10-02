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


class RecordingExecutor:
    def __init__(self) -> None:
        self.ran: list[str] = []

    async def run_universe(self, choices: dict[str, str], kind: str) -> Universe:
        universe_id = universe_id_of(choices)
        self.ran.append(universe_id)
        return Universe(
            id=universe_id, choices=choices, changed=[], kind=kind, status="done", checkpoints=["c"]
        )


def universe_id_of(choices: dict[str, str]) -> str:
    from borges.garden.executor import universe_id

    return universe_id(choices)


class StubEmitter:
    def __init__(self) -> None:
        self.seq = 7
        self.universes_finished = 0


def runtime_context(tmp_path):
    from borges.runtime.checkpoints import SqliteCheckpointStore
    from borges.runtime.context import RunContext
    from borges.runtime.db import RuntimeDb

    return RunContext("r_1", SqliteCheckpointStore(RuntimeDb(tmp_path / "rt.db")))


async def test_a_finished_universe_is_checkpointed_with_the_event_sequence(tmp_path) -> None:
    plan = make_plan()
    context = runtime_context(tmp_path)
    runner = UniverseRunner(
        None, plan, RecordingExecutor(), Garden(), StubEmitter(), 10, context, None, "root"
    )
    universe = await runner.run(plan.default_choices(), "baseline")
    rows = context.checkpoints.with_prefix("r_1", "universe:")
    assert [key for key, _, _ in rows] == [f"universe:{universe.id}"]
    assert rows[0][1] == 7 and rows[0][2]["root_id"] == "root"


async def test_a_restored_universe_is_not_executed_again(tmp_path) -> None:
    from borges.runtime.universe_checkpoint import load_restored, universe_key, universe_payload

    plan = make_plan()
    defaults = plan.default_choices()
    baseline_id = universe_id_of(defaults)
    recorded = Universe(
        id=baseline_id, choices=defaults, kind="baseline", status="done", checkpoints=["c"]
    )
    restored = load_restored(
        [(universe_key(baseline_id), 3, universe_payload(recorded, plan, "r"))]
    )
    executor, emitter, garden = RecordingExecutor(), StubEmitter(), Garden()
    runner = UniverseRunner(
        None, plan, executor, garden, emitter, 10, runtime_context(tmp_path), restored, "r"
    )
    universe = await runner.run(defaults, "baseline")
    assert executor.ran == [] and universe.id == baseline_id
    assert garden.baseline_id == baseline_id and baseline_id in garden.universes
    assert emitter.universes_finished == 1
    other = await runner.run({**defaults, "s2": "y"}, "single")
    assert executor.ran == [other.id]


async def test_a_cancelled_run_starts_no_further_universe(tmp_path) -> None:
    from borges.runtime.context import RunCancelled

    plan = make_plan()
    context = runtime_context(tmp_path)
    executor = RecordingExecutor()
    runner = UniverseRunner(None, plan, executor, Garden(), StubEmitter(), 10, context)
    context.cancel.set("stop")
    with pytest.raises(RunCancelled):
        await runner.run(plan.default_choices(), "baseline")
    assert executor.ran == []
