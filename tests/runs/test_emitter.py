from __future__ import annotations

from pathlib import Path

from borges.llm.client import UsageTotals
from borges.runs.bus import EventBus
from borges.runs.emitter import RunEmitter
from borges.runs.store import RunStore


def make(tmp_path: Path) -> tuple[RunEmitter, RunStore, EventBus]:
    store = RunStore(tmp_path)
    store.create("r_1", {})
    bus = EventBus(store)
    bus.open("r_1")
    return RunEmitter("r_1", store, bus), store, bus


async def test_assigns_increasing_seq_persists_and_publishes(tmp_path: Path) -> None:
    emitter, store, bus = make(tmp_path)
    await emitter.emit("stage", {"name": "profiling", "status": "started", "detail": ""})
    await emitter.stage("profiling", "done")
    stored = store.events("r_1")
    assert [e.seq for e in stored] == [1, 2]
    assert stored[0].ts <= stored[1].ts
    assert stored[1].data == {"name": "profiling", "status": "done", "detail": ""}
    assert bus._channels["r_1"].history == stored


async def test_usage_every_five_finished_universes(tmp_path: Path) -> None:
    emitter, store, _ = make(tmp_path)
    emitter.usage_probe = lambda: (UsageTotals(tokens_in=7, tokens_out=3, cost_usd=0.2, calls=4), 9)
    for _ in range(10):
        await emitter.emit("universe.finished", {})
    usage = [e for e in store.events("r_1") if e.type == "usage"]
    assert [u.data["universes"] for u in usage] == [5, 10]
    assert usage[0].data == {
        "tokens_in": 7,
        "tokens_out": 3,
        "cost_usd": 0.2,
        "llm_calls": 4,
        "cached_calls": 0,
        "checkpoints": 9,
        "universes": 5,
    }


async def test_usage_without_probe_is_a_noop(tmp_path: Path) -> None:
    emitter, store, _ = make(tmp_path)
    await emitter.usage()
    assert store.events("r_1") == []


async def test_personal_data_in_event_payloads_is_redacted(tmp_path: Path) -> None:
    emitter, store, _ = make(tmp_path)
    await emitter.emit("stage", {"name": "x", "detail": "failed for maria@example.com", "n": 3})
    stored = store.events("r_1")[0]
    assert stored.data == {"name": "x", "detail": "failed for [redacted:email]", "n": 3}
