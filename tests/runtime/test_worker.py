from __future__ import annotations

import asyncio

import pytest

from borges.identity.principal import Principal
from borges.identity.scopes import PUBLIC_SCOPES
from borges.runtime.jobs import RUNNING, SUCCEEDED
from borges.runtime.worker import MAX_BACKOFF_S, backoff_s
from tests.runtime.fake_runtime import REQUEST, make_fake_runtime
from tests.runtime.rig import wait_for

pytestmark = pytest.mark.timeout(60)

NAMED = Principal("caller://alice", "key", PUBLIC_SCOPES)


def test_backoff_doubles_and_is_capped() -> None:
    assert [backoff_s(2.0, n) for n in (1, 2, 3)] == [2.0, 4.0, 8.0]
    assert backoff_s(2.0, 40) == MAX_BACKOFF_S
    assert backoff_s(2.0, 0) == 2.0


async def test_heartbeat_keeps_the_lease_alive_while_a_run_is_busy(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_job_lease_s=0.3)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, NAMED, "c")
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    await asyncio.sleep(1.0)
    job = fake.runtime.queue.get(result.run_id)
    assert job.state == RUNNING and job.lease_expires > fake.runtime.queue.clock()
    assert fake.runtime.queue.reclaim_expired() == ([], [])
    await fake.runtime.stop()


async def test_a_cancel_recorded_by_another_process_reaches_the_run(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_job_lease_s=0.3)
    result = await fake.runtime.submit(REQUEST, NAMED, "c")
    await wait_for(lambda: result.run_id in fake.runtime.tokens)
    fake.runtime.queue.request_cancel(result.run_id)
    await fake.runtime.drain(30)
    assert fake.rig.store.snapshot(result.run_id).status in ("cancelled", "completed")
    await fake.runtime.stop()


async def test_a_lost_lease_stops_the_run_without_closing_it(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_job_lease_s=0.3)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, NAMED, "c")
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    with fake.runtime.db.transaction() as conn:
        conn.execute(
            "UPDATE jobs SET lease_owner = 'someone-else', lease_expires = lease_expires + 3600"
            " WHERE run_id = ?",
            (result.run_id,),
        )
    await wait_for(lambda: result.run_id not in fake.rig.orchestrator.tasks)
    events = fake.rig.store.events(result.run_id)
    assert not any(e.type in ("run.failed", "run.finished") for e in events)
    job = fake.runtime.queue.get(result.run_id)
    assert job.lease_owner == "someone-else" and job.state != SUCCEEDED
    await fake.runtime.stop()
