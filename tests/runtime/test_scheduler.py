from __future__ import annotations

from borges.runtime.scheduler import run_due, schedule_principal, submit_due
from tests.runtime.fake_runtime import make_fake_runtime
from tests.runtime.rig import wait_for


async def test_due_schedule_is_submitted_through_the_queue(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    schedule = fake.runtime.schedules.add("demo", 3600.0, "caller://nightly", "scripted", 0.0)
    submitted = await run_due(fake.runtime)
    assert len(submitted) == 1
    job = fake.runtime.queue.get(submitted[0])
    assert (job.principal, job.source, job.schedule_id) == (
        "caller://nightly",
        "schedule",
        schedule.id,
    )
    assert job.owner_key == "caller://nightly" and job.anonymous is False
    updated = fake.runtime.schedules.get(schedule.id)
    assert updated.last_run_id == submitted[0] and updated.next_run > schedule.next_run
    assert fake.runtime.schedules.due() == []
    await wait_for(lambda: fake.rig.store.snapshot(submitted[0]).status == "completed")
    await fake.runtime.stop()


async def test_a_schedule_that_is_not_due_is_left_alone(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.runtime.schedules.add("demo", 3600.0, "caller://nightly")
    assert await run_due(fake.runtime) == []
    await fake.runtime.stop()


async def test_the_same_slot_never_submits_twice(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    schedule = fake.runtime.schedules.add("demo", 3600.0, "caller://nightly", None, 0.0)
    first = await submit_due(fake.runtime, schedule)
    again = await submit_due(fake.runtime, schedule)
    assert first == again
    assert len(fake.rig.store.list_runs()) == 1
    await fake.runtime.stop()


async def test_policy_refusal_skips_the_tick_and_keeps_the_schedule_due(
    tmp_path, monkeypatch
) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    schedule = fake.runtime.schedules.add("demo", 3600.0, "caller://nightly", "nebius", 0.0)
    assert await submit_due(fake.runtime, schedule) is None
    assert [s.id for s in fake.runtime.schedules.due()] == [schedule.id]
    assert fake.rig.store.list_runs() == []
    await fake.runtime.stop()


async def test_an_unknown_case_is_skipped_and_advanced(tmp_path, monkeypatch) -> None:
    fake = make_fake_runtime(tmp_path, monkeypatch)
    fake.runtime.schedules.add("ghost", 3600.0, "caller://nightly", None, 0.0)
    assert await run_due(fake.runtime) == []
    assert fake.runtime.schedules.due() == []
    await fake.runtime.stop()


async def test_tick_runs_due_schedules_only_when_the_scheduler_is_on(tmp_path, monkeypatch) -> None:
    off = make_fake_runtime(tmp_path / "off", monkeypatch)
    off.runtime.schedules.add("demo", 3600.0, "caller://nightly", None, 0.0)
    await off.runtime.start()
    await off.runtime.tick()
    assert off.rig.store.list_runs() == []
    await off.runtime.stop()

    on = make_fake_runtime(tmp_path / "on", monkeypatch, borges_scheduler=True)
    on.runtime.schedules.add("demo", 3600.0, "caller://nightly", None, 0.0)
    await on.runtime.start()
    await wait_for(lambda: len(on.rig.store.list_runs()) == 1)
    await on.runtime.stop()


def test_schedule_principal_is_a_named_caller() -> None:
    from borges.runtime.schedules import Schedule

    schedule = Schedule("sch_1", "demo", None, 60.0, "caller://nightly", 0.0, True, 0.0, None, None)
    principal = schedule_principal(schedule)
    assert principal.id == "caller://nightly" and principal.anonymous is False
