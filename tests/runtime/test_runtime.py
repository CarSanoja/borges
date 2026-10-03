from __future__ import annotations

import asyncio

import pytest

from borges.identity.principal import ANONYMOUS, Principal
from borges.identity.scopes import PUBLIC_SCOPES
from borges.runtime.idempotency import explicit_key
from borges.runtime.jobs import CANCELLED, DEAD, FAILED, QUEUED, RUNNING, SUCCEEDED, NewJob
from tests.runtime.fake_runtime import REQUEST, make_fake_runtime, transient_error
from tests.runtime.rig import wait_for

pytestmark = pytest.mark.timeout(60)

CLIENT = "10.0.0.1"
NAMED = Principal("caller://alice", "key", PUBLIC_SCOPES)


async def settle(fake) -> None:
    await fake.runtime.drain(30)


async def test_a_submitted_run_is_queued_claimed_and_completed(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    result = await fake.runtime.submit(REQUEST, ANONYMOUS, CLIENT)
    assert result.created is True
    meta = fake.rig.store.meta(result.run_id)
    assert meta["owner_key"] == f"{ANONYMOUS.id}|{CLIENT}" and meta["source"] == "api"
    await settle(fake)
    assert fake.rig.store.snapshot(result.run_id).status == "completed"
    assert fake.runtime.queue.get(result.run_id).state == SUCCEEDED
    assert fake.runtime.checkpoints.with_prefix(result.run_id, "") == []
    await fake.runtime.stop()


async def test_duplicate_idempotency_key_returns_the_existing_run(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    key = explicit_key(NAMED.id, "same")
    first = await fake.runtime.submit(REQUEST, NAMED, CLIENT, key)
    second = await fake.runtime.submit(REQUEST, NAMED, CLIENT, key)
    assert second.created is False and second.run_id == first.run_id
    assert len(fake.rig.store.list_runs()) == 1
    await settle(fake)
    await fake.runtime.stop()


async def test_derived_key_collapses_a_double_click(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    key = fake.runtime.idempotency(ANONYMOUS, CLIENT, REQUEST, None)
    first = await fake.runtime.submit(REQUEST, ANONYMOUS, CLIENT, key)
    again = await fake.runtime.submit(REQUEST, ANONYMOUS, CLIENT, key)
    other = fake.runtime.idempotency(ANONYMOUS, "10.9.9.9", REQUEST, None)
    elsewhere = await fake.runtime.submit(REQUEST, ANONYMOUS, "10.9.9.9", other)
    assert again.run_id == first.run_id and elsewhere.run_id != first.run_id
    await settle(fake)
    await fake.runtime.stop()


async def test_unknown_case_is_refused_before_anything_is_stored(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    with pytest.raises(KeyError):
        await fake.runtime.submit(REQUEST.model_copy(update={"case_id": "nope"}), ANONYMOUS, CLIENT)
    assert fake.runtime.queue.active_run_ids() == set()
    assert fake.rig.store.list_runs() == []
    await fake.runtime.stop()


async def test_claim_time_cap_keeps_a_job_queued_until_a_slot_frees(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_max_active_runs=1)
    fake.scenario.hang = True
    first = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    second = await fake.runtime.submit(
        REQUEST, Principal("caller://bob", "key", PUBLIC_SCOPES), "x"
    )
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    assert fake.runtime.queue.get(first.run_id).state == RUNNING
    assert fake.runtime.queue.get(second.run_id).state == QUEUED
    assert fake.rig.store.snapshot(second.run_id).status == "queued"
    fake.scenario.hang = False
    await fake.runtime.cancel(first.run_id)
    fake.rig.orchestrator.tasks[first.run_id].cancel()
    await wait_for(lambda: fake.runtime.queue.get(second.run_id).state == SUCCEEDED)
    await fake.runtime.stop()


async def test_live_cap_is_enforced_at_claim_time(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(
        tmp_path, monkeypatch, borges_max_live_runs=1, borges_max_active_runs=5
    )
    live = REQUEST.model_copy(update={"llm": "nebius"})
    fake.scenario.hang = True
    a = await fake.runtime.submit(live, NAMED, CLIENT)
    b = await fake.runtime.submit(live, Principal("caller://bob", "key", PUBLIC_SCOPES), "x")
    c = await fake.runtime.submit(REQUEST, Principal("caller://eve", "key", PUBLIC_SCOPES), "y")
    await wait_for(lambda: fake.runtime.queue.get(c.run_id).state == RUNNING)
    assert fake.runtime.queue.get(a.run_id).state == RUNNING
    assert fake.runtime.queue.get(b.run_id).state == QUEUED
    await fake.runtime.stop()


async def test_cancelling_a_queued_run_ends_it_with_terminal_events(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_max_active_runs=1)
    fake.scenario.hang = True
    await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    queued = await fake.runtime.submit(
        REQUEST, Principal("caller://bob", "key", PUBLIC_SCOPES), "x"
    )
    assert await fake.runtime.cancel(queued.run_id) == "cancelled"
    events = fake.rig.store.events(queued.run_id)
    assert [e.type for e in events] == ["run.cancelled", "run.finished"]
    assert fake.rig.store.snapshot(queued.run_id).status == "cancelled"
    assert fake.rig.store.meta(queued.run_id)["status"] == "cancelled"
    assert fake.runtime.queue.get(queued.run_id).state == CANCELLED
    await fake.runtime.stop()


async def test_cancelling_a_running_run_stops_it_at_the_next_checkpoint(
    tmp_path, monkeypatch
) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    started = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: started.run_id in fake.runtime.tokens)
    assert await fake.runtime.cancel(started.run_id) == "requested"
    await settle(fake)
    snapshot = fake.rig.store.snapshot(started.run_id)
    assert snapshot.status == "cancelled"
    kinds = [e.type for e in fake.rig.store.events(started.run_id)]
    assert kinds[-2:] == ["run.cancelled", "run.finished"]
    assert fake.runtime.queue.get(started.run_id).state == CANCELLED
    await fake.runtime.stop()


async def test_transient_failure_is_retried_with_backoff_then_succeeds(
    tmp_path, monkeypatch
) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.scenario.plan_error = transient_error()
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: fake.runtime.queue.get(result.run_id).attempts >= 2)
    fake.scenario.plan_error = None
    await settle(fake)
    job = fake.runtime.queue.get(result.run_id)
    assert job.state == SUCCEEDED and job.attempts >= 2
    assert fake.rig.store.snapshot(result.run_id).status == "completed"
    assert fake.runtime.dead.entries() == []
    await fake.runtime.stop()


async def test_exhausted_retries_go_to_the_dead_letter_queue(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_job_max_attempts=2)
    fake.scenario.plan_error = transient_error()
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: fake.runtime.queue.get(result.run_id).state == DEAD)
    [entry] = fake.runtime.dead.entries()
    assert entry.run_id == result.run_id and entry.attempts == 2
    assert "ConnectError" in entry.error
    assert fake.rig.store.snapshot(result.run_id).status == "failed"
    assert fake.runtime.stats()["dead_letter_count"] == 1
    await fake.runtime.stop()


async def test_a_dead_lettered_run_can_be_requeued_and_completes(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_job_max_attempts=1)
    fake.scenario.plan_error = transient_error()
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: fake.runtime.queue.get(result.run_id).state == DEAD)
    fake.scenario.plan_error = None
    assert fake.runtime.requeue(result.run_id) is not None
    assert fake.rig.store.meta(result.run_id)["status"] == "queued"
    await wait_for(lambda: fake.runtime.queue.get(result.run_id).state == SUCCEEDED)
    snapshot = fake.rig.store.snapshot(result.run_id)
    assert snapshot.status == "completed"
    kinds = [e.type for e in fake.rig.store.events(result.run_id)]
    assert kinds.count("run.finished") == 1 and kinds.count("run.failed") == 0
    assert fake.runtime.dead.entries() == []
    await fake.runtime.stop()


async def test_a_permanent_failure_is_not_retried(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.scenario.plan_error = ValueError("bad plan")
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await settle(fake)
    job = fake.runtime.queue.get(result.run_id)
    assert (job.state, job.attempts) == (FAILED, 1)
    assert fake.runtime.dead.entries() == []
    await fake.runtime.stop()


async def test_missing_upload_fails_the_run_cleanly(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.rig.store.create("r_up", {"status": "queued"})
    request = REQUEST.model_copy(update={"case_id": None, "upload_id": "gone"})
    fake.runtime.queue.submit(
        NewJob(
            run_id="r_up",
            principal=NAMED.id,
            owner_key=NAMED.id,
            anonymous=False,
            live=False,
            request=request.model_dump_json(exclude_none=True),
            max_attempts=3,
            upload_id="gone",
        )
    )
    await fake.runtime.start()
    await settle(fake)
    assert fake.runtime.queue.get("r_up").state == FAILED
    assert fake.rig.store.snapshot("r_up").status == "failed"
    await fake.runtime.stop()


async def test_stats_track_the_queue(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_max_active_runs=1)
    fake.scenario.hang = True
    await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await fake.runtime.submit(REQUEST, Principal("caller://bob", "key", PUBLIC_SCOPES), "x")
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    stats = fake.runtime.stats()
    assert stats["queue_depth"] == 1 and stats["active_workers"] == 1
    assert stats["oldest_job_age_s"] is not None and stats["dead_letter_count"] == 0
    await fake.runtime.stop()


async def test_graceful_stop_releases_the_lease_for_the_next_process(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    await fake.runtime.stop()
    job = fake.runtime.queue.get(result.run_id)
    assert (job.state, job.attempts, job.resume_reason) == (QUEUED, 0, "restart")
    assert not any(e.type == "run.finished" for e in fake.rig.store.events(result.run_id))


async def test_a_job_whose_leases_keep_expiring_ends_in_the_dead_letter_queue(
    tmp_path, monkeypatch
) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_job_max_attempts=1)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    fake.runtime.queue.release = lambda *args, **kwargs: False
    fake.rig.orchestrator.tasks[result.run_id].cancel()
    await fake.runtime.stop()
    with fake.runtime.db.transaction() as conn:
        conn.execute("UPDATE jobs SET lease_expires = 1 WHERE run_id = ?", (result.run_id,))
    fake.runtime.maintain()
    assert fake.runtime.queue.get(result.run_id).state == DEAD
    [entry] = fake.runtime.dead.entries()
    assert "lease expired" in entry.error
    kinds = [e.type for e in fake.rig.store.events(result.run_id)]
    assert kinds[-2:] == ["run.failed", "run.finished"]


async def test_maintain_marks_reclaimed_runs_queued(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.scenario.hang = True
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await wait_for(lambda: fake.scenario.entered_plan.is_set())
    fake.runtime.queue.release = lambda *args, **kwargs: False
    fake.rig.orchestrator.tasks[result.run_id].cancel()
    await fake.runtime.stop()
    with fake.runtime.db.transaction() as conn:
        conn.execute("UPDATE jobs SET lease_expires = 1 WHERE run_id = ?", (result.run_id,))
    fake.runtime.maintain()
    assert fake.runtime.queue.get(result.run_id).state == QUEUED
    assert fake.rig.store.meta(result.run_id)["status"] == "queued"


async def test_recover_expires_the_leases_of_dead_local_processes(tmp_path, monkeypatch) -> None:
    import socket

    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.runtime.queue.submit(
        NewJob(
            run_id="r_x",
            principal=NAMED.id,
            owner_key=NAMED.id,
            anonymous=False,
            live=False,
            request="{}",
            max_attempts=3,
        )
    )
    fake.runtime.queue.claim(f"{socket.gethostname()}:999999:aa", 600, lambda job, running: True)
    assert fake.runtime.recover() == 1
    assert fake.runtime.queue.reclaim_expired() == (["r_x"], [])


async def test_requeue_of_an_unknown_run_is_none(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    assert fake.runtime.requeue("r_nope") is None


async def test_a_run_waiting_after_a_restart_is_not_reported_as_interrupted(
    tmp_path, monkeypatch
) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch, borges_max_active_runs=0)
    result = await fake.runtime.submit(REQUEST, NAMED, CLIENT)
    await fake.runtime.stop()
    fake.rig.bus._channels.clear()
    assert not fake.rig.bus.is_live(result.run_id)
    await fake.runtime.start()
    assert fake.rig.bus.is_live(result.run_id)
    stream = fake.rig.bus.subscribe(result.run_id)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(stream), 0.3)
    await stream.aclose()
    await fake.runtime.stop()
