from __future__ import annotations

import pytest

from borges.runtime.schedules import MIN_EVERY_S, ScheduleStore, parse_every


@pytest.fixture
def store(db, clock) -> ScheduleStore:
    return ScheduleStore(db, clock)


def test_parse_every() -> None:
    assert parse_every("24h") == 86400.0
    assert parse_every("90m") == 5400.0
    assert parse_every("7d") == 7 * 86400.0


@pytest.mark.parametrize("raw", ["never", "", "soon", "10s", "0h"])
def test_parse_every_rejects_what_is_not_a_sane_interval(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_every(raw)
    assert MIN_EVERY_S == 60.0


def test_a_new_schedule_first_runs_after_one_interval(store: ScheduleStore, clock) -> None:
    schedule = store.add("checkout_ab", 3600.0, "operator")
    assert schedule.next_run == clock.now + 3600.0
    assert schedule.id.startswith("sch_") and schedule.enabled
    assert store.get(schedule.id) == schedule
    assert store.entries() == [schedule]
    assert schedule.as_dict()["case_id"] == "checkout_ab"


def test_due_returns_schedules_whose_time_has_come(store: ScheduleStore, clock) -> None:
    soon = store.add("a", 100.0, "p", first_in_s=10.0)
    store.add("b", 100.0, "p", first_in_s=500.0)
    assert store.due() == []
    clock.advance(10)
    assert [s.id for s in store.due()] == [soon.id]


def test_advance_moves_to_the_next_future_slot_and_records_the_run(
    store: ScheduleStore, clock
) -> None:
    schedule = store.add("a", 100.0, "p", first_in_s=0.0)
    clock.advance(350)
    store.advance(schedule, "r_1")
    updated = store.get(schedule.id)
    assert updated.next_run > clock.now and updated.next_run - clock.now <= 100.0
    assert updated.last_run_id == "r_1" and updated.last_run_at == clock.now


def test_advance_without_a_run_keeps_the_last_one(store: ScheduleStore, clock) -> None:
    schedule = store.add("a", 100.0, "p", first_in_s=0.0)
    store.advance(schedule, "r_1")
    clock.advance(200)
    store.advance(store.get(schedule.id), None)
    assert store.get(schedule.id).last_run_id == "r_1"


def test_remove(store: ScheduleStore) -> None:
    schedule = store.add("a", 100.0, "p")
    assert store.remove(schedule.id) is True
    assert store.remove(schedule.id) is False
    assert store.entries() == []
