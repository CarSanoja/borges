from __future__ import annotations

from borges.runs.bus import EventBus
from borges.runs.events import Event
from borges.runs.store import RunStore
from borges.runtime.finalize import append_terminal


def make(tmp_path) -> tuple[RunStore, EventBus]:
    store = RunStore(tmp_path)
    store.create("r1", {"status": "queued"})
    return store, EventBus(store)


def test_cancelled_run_gets_its_two_terminal_events(tmp_path) -> None:
    store, bus = make(tmp_path)
    append_terminal(store, bus, "r1", "cancelled", "by request")
    events = store.events("r1")
    assert [e.type for e in events] == ["run.cancelled", "run.finished"]
    assert events[0].data == {"reason": "by request"}
    assert events[1].data["status"] == "cancelled"
    assert store.meta("r1")["status"] == "cancelled"
    assert store.snapshot("r1").status == "cancelled"


def test_failed_run_records_the_error(tmp_path) -> None:
    store, bus = make(tmp_path)
    append_terminal(store, bus, "r1", "failed", "no data")
    assert [e.type for e in store.events("r1")] == ["run.failed", "run.finished"]
    assert store.snapshot("r1").error == "no data"


def test_a_run_that_already_ended_is_not_closed_twice(tmp_path) -> None:
    store, bus = make(tmp_path)
    store.append(
        Event(seq=1, ts=1.0, run_id="r1", type="run.finished", data={"status": "completed"})
    )
    append_terminal(store, bus, "r1", "failed", "late")
    assert len(store.events("r1")) == 1
    assert store.meta("r1")["status"] == "failed"


def test_unknown_run_is_ignored(tmp_path) -> None:
    store, bus = make(tmp_path)
    append_terminal(store, bus, "ghost", "failed")
