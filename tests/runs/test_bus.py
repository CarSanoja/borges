from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from borges.runs.bus import EventBus
from borges.runs.events import Event
from borges.runs.store import RunStore


def event(seq: int, event_type: str = "stage", run_id: str = "r_1") -> Event:
    return Event(seq=seq, ts=float(seq), run_id=run_id, type=event_type)


@pytest.fixture
def bus(tmp_path: Path) -> EventBus:
    store = RunStore(tmp_path)
    store.create("r_1", {})
    return EventBus(store)


async def collect(bus: EventBus, run_id: str = "r_1", from_seq: int = 0) -> list[int]:
    return [e.seq async for e in bus.subscribe(run_id, from_seq)]


async def test_live_subscriber_gets_history_then_live_events(bus: EventBus) -> None:
    bus.open("r_1")
    bus.publish(event(1))
    bus.publish(event(2))
    task = asyncio.create_task(collect(bus))
    await asyncio.sleep(0)
    bus.publish(event(3))
    bus.publish(event(4, "run.finished"))
    assert await task == [1, 2, 3, 4]


async def test_many_subscribers_each_get_everything(bus: EventBus) -> None:
    bus.open("r_1")
    tasks = [asyncio.create_task(collect(bus)) for _ in range(3)]
    await asyncio.sleep(0)
    for seq in (1, 2):
        bus.publish(event(seq))
    bus.publish(event(3, "run.finished"))
    assert await asyncio.gather(*tasks) == [[1, 2, 3]] * 3


async def test_from_seq_skips_seen_events(bus: EventBus) -> None:
    bus.open("r_1")
    for seq in (1, 2, 3):
        bus.publish(event(seq))
    task = asyncio.create_task(collect(bus, from_seq=2))
    await asyncio.sleep(0)
    bus.publish(event(4, "run.failed"))
    assert await task == [3, 4]


async def test_stops_on_run_failed(bus: EventBus) -> None:
    bus.open("r_1")
    task = asyncio.create_task(collect(bus))
    await asyncio.sleep(0)
    bus.publish(event(1, "run.failed"))
    assert await task == [1]


async def test_finished_runs_are_served_from_the_store(bus: EventBus) -> None:
    for seq, kind in ((1, "run.started"), (2, "stage"), (3, "run.finished")):
        bus.store.append(event(seq, kind))
    assert not bus.is_live("r_1")
    assert await collect(bus) == [1, 2, 3]
    assert await collect(bus, from_seq=2) == [3]


async def test_finish_releases_memory_and_late_subscribers_use_the_store(bus: EventBus) -> None:
    bus.open("r_1")
    for seq, kind in ((1, "stage"), (2, "run.finished")):
        stored = event(seq, kind)
        bus.store.append(stored)
        bus.publish(stored)
    assert not bus.is_live("r_1")
    assert await collect(bus) == [1, 2]


async def test_unknown_run_raises(bus: EventBus) -> None:
    with pytest.raises(KeyError):
        await collect(bus, "missing")


async def test_cancelled_subscriber_is_unregistered(bus: EventBus) -> None:
    bus.open("r_1")
    task = asyncio.create_task(collect(bus))
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert bus._channels["r_1"].queues == set()
