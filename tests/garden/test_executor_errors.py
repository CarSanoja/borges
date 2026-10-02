from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from borges.garden.executor import GardenExecutor
from tests.garden.fakes import FakeBackend, install_fake_harness, make_plan


@pytest.fixture(autouse=True)
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_harness(monkeypatch)


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


async def test_error_prefers_parsed_exception_over_stderr_warning() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    real_run = backend.run

    async def warns_then_raises(parent: Any, command: Any, **kwargs: Any) -> Any:
        result = await real_run(parent, command, **kwargs)
        if command[-1] == "s2:y":
            return replace(
                result,
                exit_code=1,
                stdout="ERROR ValueError: bad column",
                stderr="UserWarning: something harmless",
            )
        return result

    backend.run = warns_then_raises
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    universe = await executor.run_universe({**plan.default_choices(), "s2": "y"}, "single")
    assert universe.status == "failed"
    assert "ValueError: bad column" in (universe.error or "")
    assert "harmless" not in (universe.error or "")


async def test_error_falls_back_to_exit_code() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    real_run = backend.run

    async def silent_failure(parent: Any, command: Any, **kwargs: Any) -> Any:
        result = await real_run(parent, command, **kwargs)
        if command[-1] == "s2:y":
            return replace(result, exit_code=7, stdout="", stderr="")
        return result

    backend.run = silent_failure
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    universe = await executor.run_universe({**plan.default_choices(), "s2": "y"}, "single")
    assert "exit code 7" in (universe.error or "")


async def test_step_timeout_comes_from_the_constructor() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    seen: list[float] = []
    real_run = backend.run

    async def spy(parent: Any, command: Any, **kwargs: Any) -> Any:
        seen.append(kwargs["timeout_s"])
        return await real_run(parent, command, **kwargs)

    backend.run = spy
    executor = GardenExecutor(backend, plan, b"d", step_timeout_s=17.5)
    await executor.setup()
    await executor.run_universe(plan.default_choices(), "baseline")
    assert seen and set(seen) == {17.5}


async def test_stderr_fallback_carries_no_host_paths() -> None:
    plan = make_plan()
    backend = FakeBackend(plan)
    real_run = backend.run

    async def crash(parent: Any, command: Any, **kwargs: Any) -> Any:
        result = await real_run(parent, command, **kwargs)
        if command[-1] == "s2:y":
            stderr = (
                'File "/Users/a/.venv/lib/python3.13/site-packages/pandas/m.py", line 9\nKeyError'
            )
            return replace(result, exit_code=1, stdout="", stderr=stderr)
        return result

    backend.run = crash
    executor = GardenExecutor(backend, plan, b"d")
    await executor.setup()
    universe = await executor.run_universe({**plan.default_choices(), "s2": "y"}, "single")
    assert "KeyError" in (universe.error or "")
    assert "/Users/" not in (universe.error or "")
