from __future__ import annotations

import time
from pathlib import Path

from borges.llm.client import Usage, UsageTotals
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


async def test_a_failed_run_reports_what_it_spent_before_failing(tmp_path: Path) -> None:
    store, bus, emitter = parts(tmp_path)
    totals = UsageTotals()
    totals.add(Usage(model="m", tokens_in=3000, tokens_out=4096, cost_usd=0.0153))
    emitter.usage_probe = lambda: (totals, 0)
    await finish(store, bus, emitter, time.monotonic(), "planner: output truncated", None)
    events = store.events("r_1")
    assert [e.type for e in events] == ["usage", "run.failed", "run.finished"]
    assert events[0].data["cost_usd"] == 0.0153 and events[0].data["tokens_out"] == 4096
