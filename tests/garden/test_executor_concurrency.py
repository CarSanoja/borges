from __future__ import annotations

import asyncio
from typing import Any

import pytest

from borges.garden.executor import GardenExecutor
from tests.garden.fakes import FakeBackend, install_fake_harness, make_plan
from tests.garden.test_executor import Recorder


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


async def test_concurrent_universes_do_not_duplicate_work() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    executor = GardenExecutor(backend, plan, b"d", concurrency=6)
    await executor.setup()
    base = plan.default_choices()
    universes = await asyncio.gather(
        executor.run_universe(base, "baseline"),
        executor.run_universe({**base, "s3": "n"}, "single"),
        executor.run_universe({**base, "s3": "o"}, "single"),
        executor.run_universe({**base, "s3": "n"}, "single"),
    )
    assert all(u.status == "done" for u in universes)
    assert len(backend.runs) == len(set(backend.runs)) == 5
    assert executor.checkpoints_created == 6


async def test_concurrency_is_bounded() -> None:
    plan = make_plan()
    active = 0
    peak = 0
    recorder = Recorder()

    async def emit(event_type: str, data: dict[str, Any]) -> None:
        nonlocal active, peak
        if event_type == "universe.started":
            active += 1
            peak = max(peak, active)
        if event_type == "universe.finished":
            active -= 1
        await recorder(event_type, data)

    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=emit, concurrency=2)
    await executor.setup()
    base = plan.default_choices()
    await asyncio.gather(
        *(
            executor.run_universe({**base, step: option}, "single")
            for step, option in [("s1", "b"), ("s2", "y"), ("s3", "n"), ("s3", "o")]
        )
    )
    assert peak == 2
