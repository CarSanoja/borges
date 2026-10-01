from __future__ import annotations

import asyncio
from typing import Any

import pytest

from borges.garden.executor import GardenExecutor, universe_id
from tests.garden.fakes import FakeBackend, estimate_for, install_fake_harness, make_plan


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, event_type: str, data: dict[str, Any]) -> None:
        self.events.append((event_type, data))

    def of(self, event_type: str) -> list[dict[str, Any]]:
        return [d for t, d in self.events if t == event_type]


def test_universe_id_is_stable_and_order_independent() -> None:
    a = universe_id({"s1": "a", "s2": "x"})
    assert a == universe_id({"s2": "x", "s1": "a"})
    assert a.startswith("u_") and len(a) == 12
    assert a != universe_id({"s1": "b", "s2": "x"})


async def test_setup_emits_root_checkpoint() -> None:
    plan = make_plan()
    recorder = Recorder()
    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=recorder)
    root = await executor.setup()
    assert executor.root == root
    assert recorder.of("checkpoint.created") == [
        {
            "checkpoint_id": root.id,
            "parent_id": None,
            "step_id": None,
            "option_id": None,
            "depth": 0,
            "duration_s": recorder.of("checkpoint.created")[0]["duration_s"],
        }
    ]
    assert executor.checkpoints_created == 1


async def test_baseline_universe() -> None:
    plan = make_plan()
    recorder = Recorder()
    executor = GardenExecutor(FakeBackend(plan), plan, b"d", emit=recorder)
    await executor.setup()
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.status == "done"
    assert universe.changed == []
    assert universe.verdict == "SHIP"
    assert universe.flipped is False
    assert executor.baseline_verdict == "SHIP"
    assert universe.result is not None and universe.result.estimate == estimate_for(
        universe.choices
    )
    assert len(universe.checkpoints) == 3
    assert [t.step_id for t in universe.traces] == ["s1", "s2", "s3"]
    assert [e["universe"]["status"] for e in recorder.of("universe.started")] == ["running"]
    assert recorder.of("universe.finished")[0]["universe"]["id"] == universe.id
    depths = [e["depth"] for e in recorder.of("checkpoint.created")]
    assert depths == [0, 1, 2, 3]


async def test_flipped_flag_and_changed() -> None:
    plan = make_plan()
    executor = GardenExecutor(FakeBackend(plan), plan, b"d")
    await executor.setup()
    await executor.run_universe(plan.default_choices(), "baseline")
    flipped = await executor.run_universe({**plan.default_choices(), "s2": "y"}, "single")
    kept = await executor.run_universe({**plan.default_choices(), "s1": "b"}, "single")
    assert flipped.changed == ["s2"]
    assert flipped.verdict == "DON'T SHIP" and flipped.flipped is True
    assert kept.verdict == "SHIP" and kept.flipped is False


async def test_prefix_sharing_creates_fewer_checkpoints() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    base = plan.default_choices()
    await executor.run_universe(base, "baseline")
    assert executor.checkpoints_created == 4
    await executor.run_universe({**base, "s3": "n"}, "single")
    assert executor.checkpoints_created == 5
    await executor.run_universe({**base, "s3": "o"}, "single")
    assert executor.checkpoints_created == 6
    await executor.run_universe({**base, "s1": "b"}, "single")
    assert executor.checkpoints_created == 9
    await executor.run_universe(base, "baseline")
    assert executor.checkpoints_created == 9
    assert len(backend.runs) == 8


async def test_no_reuse_recomputes_fresh_chain() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    executor = GardenExecutor(backend, plan, b"d", reuse_prefixes=False)
    await executor.setup()
    base = plan.default_choices()
    first = await executor.run_universe(base, "baseline")
    second = await executor.run_universe(base, "baseline")
    assert len(backend.runs) == 6
    assert executor.checkpoints_created == 7
    assert set(first.checkpoints).isdisjoint(second.checkpoints)


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


async def test_failure_marks_universe_failed_and_never_raises() -> None:
    plan = make_plan()
    backend = FakeBackend(plan, fail={("s2", "y")})
    recorder = Recorder()
    executor = GardenExecutor(backend, plan, b"d", emit=recorder)
    await executor.setup()
    base = plan.default_choices()
    broken = await executor.run_universe({**base, "s2": "y"}, "single")
    assert broken.status == "failed"
    assert broken.result is None and broken.verdict is None and broken.flipped is None
    assert broken.error is not None and "boom" in broken.error and "s2" in broken.error
    assert len(broken.checkpoints) == 1
    again = await executor.run_universe({**base, "s2": "y", "s3": "n"}, "single")
    assert again.status == "failed"
    assert len([r for r in backend.runs if r[1] == "s2:y"]) == 1
    assert recorder.of("universe.finished")[-1]["universe"]["status"] == "failed"


async def test_backend_exception_becomes_failure() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)

    async def explode(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("sandbox down")

    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    backend.run = explode
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.status == "failed"
    assert "sandbox down" in (universe.error or "")


async def test_run_universe_requires_setup() -> None:
    plan = make_plan()
    executor = GardenExecutor(FakeBackend(plan), plan, b"d")
    with pytest.raises(RuntimeError):
        await executor.run_universe(plan.default_choices(), "baseline")


async def test_transient_backend_failure_is_not_cached() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    real_run = backend.run
    attempts = {"n": 0}

    async def flaky(*args: Any, **kwargs: Any) -> Any:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("429 rate limited")
        return await real_run(*args, **kwargs)

    backend.run = flaky
    first = await executor.run_universe(plan.default_choices(), "baseline")
    second = await executor.run_universe(plan.default_choices(), "baseline")
    assert first.status == "failed"
    assert second.status == "done"


async def test_changed_option_code_is_recomputed() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    await executor.run_universe(plan.default_choices(), "baseline")
    before = len(backend.runs)
    plan.step("s1").default.code = "def apply(df, ctx):\n    return df\n"
    await executor.run_universe(plan.default_choices(), "baseline")
    assert len(backend.runs) - before == len(plan.steps)


async def test_step_without_trace_fails() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    real_run = backend.run

    async def silent(*args: Any, **kwargs: Any) -> Any:
        run = await real_run(*args, **kwargs)
        return type(run)(run.checkpoint, 0, "", "", 0.1)

    backend.run = silent
    universe = await executor.run_universe(plan.default_choices(), "baseline")
    assert universe.status == "failed"
    assert "no trace" in (universe.error or "")
