from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from borges.runs.models import RunRequest
from borges.runtime.checkpoints import SqliteCheckpointStore
from borges.runtime.context import RunCancelled, RunContext, RunRetry
from borges.runtime.db import RuntimeDb
from tests.runs.engine_fakes import Scenario, install
from tests.runs.fakes import make_rig

REQUEST = RunRequest(case_id="demo")


@pytest.fixture
def scenario(monkeypatch: pytest.MonkeyPatch) -> Scenario:
    value = Scenario()
    install(monkeypatch, value)
    return value


def context(tmp_path: Path, **fields) -> RunContext:
    db = RuntimeDb(tmp_path / "rt.db")
    return RunContext("r_ctx", SqliteCheckpointStore(db), **fields)


async def test_cancel_at_a_checkpoint_ends_the_run_cancelled(tmp_path, scenario) -> None:
    rig = make_rig(tmp_path)
    ctx = context(tmp_path)
    ctx.cancel.set("by request")
    snapshot = await rig.orchestrator.execute("r_ctx", REQUEST, context=ctx)
    assert snapshot.status == "cancelled"
    kinds = [e.type for e in rig.store.events("r_ctx")]
    assert kinds[-2:] == ["run.cancelled", "run.finished"]
    assert rig.store.events("r_ctx")[-2].data == {"reason": "by request"}
    assert rig.store.meta("r_ctx")["status"] == "cancelled"
    assert not rig.bus.is_live("r_ctx") and rig.backend.closed


async def test_a_transient_failure_with_attempts_left_raises_retry_and_stays_open(
    tmp_path, scenario
) -> None:
    rig = make_rig(tmp_path)
    scenario.plan_error = httpx.ConnectError("down")
    ctx = context(tmp_path, attempt=1, max_attempts=3)
    with pytest.raises(RunRetry, match="ConnectError"):
        await rig.orchestrator.execute("r_ctx", REQUEST, context=ctx)
    kinds = [e.type for e in rig.store.events("r_ctx")]
    assert "run.failed" not in kinds and "run.finished" not in kinds
    assert rig.store.meta("r_ctx")["status"] == "running"
    assert rig.bus.is_live("r_ctx") and rig.backend.closed


async def test_the_last_attempt_fails_for_good_and_marks_the_context(tmp_path, scenario) -> None:
    rig = make_rig(tmp_path)
    scenario.plan_error = httpx.ConnectError("down")
    ctx = context(tmp_path, attempt=3, max_attempts=3)
    snapshot = await rig.orchestrator.execute("r_ctx", REQUEST, context=ctx)
    assert snapshot.status == "failed" and ctx.transient_failure is True
    assert [e.type for e in rig.store.events("r_ctx")][-2:] == ["run.failed", "run.finished"]


async def test_a_permanent_failure_is_not_marked_transient(tmp_path, scenario) -> None:
    rig = make_rig(tmp_path)
    scenario.plan_error = ValueError("bad")
    ctx = context(tmp_path, attempt=1, max_attempts=3)
    snapshot = await rig.orchestrator.execute("r_ctx", REQUEST, context=ctx)
    assert snapshot.status == "failed" and ctx.transient_failure is False


async def test_a_managed_run_cancelled_by_the_loop_is_left_resumable(tmp_path, scenario) -> None:
    rig = make_rig(tmp_path)
    scenario.hang = True
    task = rig.orchestrator.launch("r_ctx", REQUEST, context=context(tmp_path))
    await scenario.entered_plan.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    kinds = [e.type for e in rig.store.events("r_ctx")]
    assert kinds[0] == "run.started" and "stage" in kinds
    assert "run.finished" not in kinds and "run.failed" not in kinds
    assert not rig.bus.is_live("r_ctx") and rig.backend.closed


async def test_without_a_context_a_cancelled_run_still_fails_with_events(
    tmp_path, scenario
) -> None:
    rig = make_rig(tmp_path)
    scenario.hang = True
    task = rig.orchestrator.launch("r_ctx", REQUEST)
    await scenario.entered_plan.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert [e.type for e in rig.store.events("r_ctx")][-2:] == ["run.failed", "run.finished"]


async def test_resume_emits_run_resumed_and_does_not_announce_again(tmp_path, scenario) -> None:
    rig = make_rig(tmp_path)
    first = context(tmp_path)
    scenario.hang = True
    task = rig.orchestrator.launch("r_ctx", REQUEST, context=first)
    await scenario.entered_plan.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    scenario.hang = False
    resumed = context(tmp_path, attempt=2, resume_reason="restart")
    snapshot = await rig.orchestrator.execute("r_ctx", REQUEST, context=resumed)
    kinds = [e.type for e in rig.store.events("r_ctx")]
    assert snapshot.status == "completed" and snapshot.resumed == 1
    assert kinds.count("run.started") == 1 and kinds.count("run.resumed") == 1
    stages = [
        (e.data["name"], e.data["status"]) for e in rig.store.events("r_ctx") if e.type == "stage"
    ]
    assert len(stages) == len(set(stages))


def test_run_cancelled_carries_its_reason() -> None:
    assert str(RunCancelled("x")) == "x"
