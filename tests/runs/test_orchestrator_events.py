from __future__ import annotations

import time
from pathlib import Path

from borges.runs.bus import EventBus
from borges.runs.emitter import RunEmitter
from borges.runs.orchestrator_events import finish
from borges.runs.store import RunStore


def parts(tmp_path: Path):
    store = RunStore(tmp_path)
    store.create("r_1", {"status": "running"})
    bus = EventBus(store)
    bus.open("r_1")
    return store, bus, RunEmitter("r_1", store, bus)


async def test_finish_completed(tmp_path: Path) -> None:
    store, bus, emitter = parts(tmp_path)
    await finish(store, bus, emitter, time.monotonic(), None, None)
    assert [e.type for e in store.events("r_1")] == ["run.finished"]
    assert store.events("r_1")[0].data["status"] == "completed"
    assert store.meta("r_1")["status"] == "completed"


async def test_finish_failed_records_the_error(tmp_path: Path) -> None:
    store, bus, emitter = parts(tmp_path)
    await finish(store, bus, emitter, time.monotonic(), "boom", None)
    assert [e.type for e in store.events("r_1")] == ["run.failed", "run.finished"]
    assert store.meta("r_1")["status"] == "failed"


async def test_finish_cancelled_wins_over_an_error(tmp_path: Path) -> None:
    store, bus, emitter = parts(tmp_path)
    await finish(store, bus, emitter, time.monotonic(), "ignored", None, "by request")
    events = store.events("r_1")
    assert [e.type for e in events] == ["run.cancelled", "run.finished"]
    assert events[0].data == {"reason": "by request"} and events[1].data["status"] == "cancelled"
    assert store.meta("r_1")["status"] == "cancelled"
