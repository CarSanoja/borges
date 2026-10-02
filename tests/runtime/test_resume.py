from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path

import pytest

from borges.garden.executor import GardenExecutor
from borges.identity.principal import ANONYMOUS
from borges.runs.models import RunRequest
from borges.runtime.jobs import QUEUED, RUNNING, SUCCEEDED
from borges.runtime.universe_checkpoint import UNIVERSE_PREFIX
from tests.runtime.rig import Rig, make_rig, wait_for

pytestmark = pytest.mark.timeout(240)

REQUEST = RunRequest(case_id="checkout_ab", llm="scripted")


@pytest.fixture
def executed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    real = GardenExecutor.run_universe

    async def spy(self, choices, kind):
        universe = await real(self, choices, kind)
        calls.append(universe.id)
        return universe

    monkeypatch.setattr(GardenExecutor, "run_universe", spy)
    return calls


def checkpointed(rig: Rig, run_id: str) -> int:
    return len(rig.runtime.checkpoints.with_prefix(run_id, UNIVERSE_PREFIX))


async def finished(rig: Rig, run_id: str):
    await rig.runtime.drain(180)
    return rig.store.events(run_id), rig.store.snapshot(run_id)


async def test_killed_run_resumes_to_the_same_universes_and_flip(
    tmp_path: Path, executed: list[str]
) -> None:
    plain = make_rig(tmp_path / "plain")
    created = await plain.runtime.submit(REQUEST, ANONYMOUS, "c")
    plain_events, plain_snapshot = await finished(plain, created.run_id)
    await plain.runtime.stop()
    assert plain_snapshot.status == "completed" and len(plain_snapshot.garden.universes) == 7
    executed.clear()

    first = make_rig(tmp_path / "crash")
    run_id = (await first.runtime.submit(REQUEST, ANONYMOUS, "c")).run_id
    await wait_for(lambda: checkpointed(first, run_id) >= 3)
    first.orchestrator.tasks[run_id].cancel()
    await first.runtime.stop()
    await asyncio.sleep(0.1)
    assert first.store.meta(run_id)["status"] != "failed"
    assert not any(e.type in ("run.failed", "run.finished") for e in first.store.events(run_id))
    done_before = checkpointed(first, run_id)
    assert 3 <= done_before < 7
    executed.clear()

    second = make_rig(tmp_path / "crash")
    await second.runtime.start()
    events, snapshot = await finished(second, run_id)
    await second.runtime.stop()

    assert snapshot.status == "completed"
    assert sorted(snapshot.garden.universes) == sorted(plain_snapshot.garden.universes)
    assert snapshot.flip.universe_id == plain_snapshot.flip.universe_id == "u_4e00fbb461"
    assert snapshot.resumed >= 1
    verification_runs = 2
    assert len(executed) == 7 - done_before + verification_runs
    restored = {u for u in plain_snapshot.garden.universes} & set(executed)
    assert len(restored) <= 7 - done_before + 1
    assert second.runtime.queue.get(run_id).state == SUCCEEDED


async def test_resumed_event_log_has_no_duplicates_and_replays(tmp_path: Path) -> None:
    first = make_rig(tmp_path)
    run_id = (await first.runtime.submit(REQUEST, ANONYMOUS, "c")).run_id
    await wait_for(lambda: checkpointed(first, run_id) >= 2)
    first.orchestrator.tasks[run_id].cancel()
    await first.runtime.stop()
    second = make_rig(tmp_path)
    await second.runtime.start()
    events, snapshot = await finished(second, run_id)
    await second.runtime.stop()

    seqs = [e.seq for e in events]
    assert seqs == sorted(set(seqs))
    kinds = Counter(e.type for e in events)
    assert kinds["run.started"] == 1 and kinds["run.finished"] == 1
    assert kinds["run.resumed"] >= 1 and kinds["report.ready"] == 1
    finals = Counter(e.data["universe"]["id"] for e in events if e.type == "universe.finished")
    assert set(finals.values()) == {1}
    nodes = Counter(e.data["checkpoint_id"] for e in events if e.type == "checkpoint.created")
    assert set(nodes.values()) == {1}
    created = {e.data["checkpoint_id"] for e in events if e.type == "checkpoint.created"}
    parents = {e.data["parent_id"] for e in events if e.type == "checkpoint.created"} - {None}
    assert parents <= created
    for universe in snapshot.garden.universes.values():
        assert set(universe.checkpoints) <= created
    assert second.store.snapshot(run_id).model_dump() == snapshot.model_dump()


async def test_crash_without_release_is_recovered_when_the_lease_expires(tmp_path: Path) -> None:
    first = make_rig(tmp_path, borges_job_lease_s=0.4)
    first.runtime.queue.release = lambda *args, **kwargs: False
    run_id = (await first.runtime.submit(REQUEST, ANONYMOUS, "c")).run_id
    await wait_for(lambda: checkpointed(first, run_id) >= 2)
    first.orchestrator.tasks[run_id].cancel()
    await first.runtime.stop()
    assert first.runtime.queue.get(run_id).state == RUNNING

    second = make_rig(tmp_path, borges_job_lease_s=0.4)
    await second.runtime.start()
    await wait_for(lambda: second.runtime.queue.get(run_id).state != QUEUED, 5)
    events, snapshot = await finished(second, run_id)
    await second.runtime.stop()
    assert snapshot.status == "completed" and snapshot.resumed >= 1
    assert second.runtime.queue.get(run_id).resume_reason == "lease_expired"


async def test_restart_before_any_event_just_starts_the_run(tmp_path: Path) -> None:
    rig = make_rig(tmp_path, borges_job_lease_s=0.3)
    run_id = (await rig.runtime.submit(REQUEST, ANONYMOUS, "c")).run_id
    rig.runtime.jobs[run_id].cancel()
    await rig.runtime.stop()
    assert rig.store.events(run_id) == []
    again = make_rig(tmp_path, borges_job_lease_s=0.3)
    await again.runtime.start()
    events, snapshot = await finished(again, run_id)
    await again.runtime.stop()
    assert snapshot.status == "completed" and snapshot.resumed == 0
