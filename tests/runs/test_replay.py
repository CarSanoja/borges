from __future__ import annotations

import pytest

from borges.runs import replay
from borges.runs.events import Event
from borges.runs.replay import replay_events


def events(*timestamps: float) -> list[Event]:
    return [Event(seq=i + 1, ts=ts, run_id="r", type="stage") for i, ts in enumerate(timestamps)]


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(replay.asyncio, "sleep", fake_sleep)
    return recorded


async def test_yields_all_events_in_order(sleeps: list[float]) -> None:
    out = [e.seq async for e in replay_events(events(0, 1, 2))]
    assert out == [1, 2, 3]


async def test_gaps_follow_timestamps_divided_by_speed(sleeps: list[float]) -> None:
    _ = [e async for e in replay_events(events(10.0, 10.5, 11.5), speed=2.0)]
    assert sleeps == [0.25, 0.5]


async def test_gaps_are_capped(sleeps: list[float]) -> None:
    _ = [e async for e in replay_events(events(0, 30, 31), max_gap_s=1.5)]
    assert sleeps == [1.5, 1.0]


async def test_out_of_order_timestamps_do_not_sleep_negative(sleeps: list[float]) -> None:
    _ = [e async for e in replay_events(events(5, 4))]
    assert sleeps == [0.0]


async def test_empty_stream_and_invalid_speed(sleeps: list[float]) -> None:
    assert [e async for e in replay_events([])] == []
    with pytest.raises(ValueError):
        _ = [e async for e in replay_events(events(0), speed=0)]


async def test_preparation_events_are_compressed(sleeps: list[float]) -> None:
    stream = [
        Event(seq=1, ts=0.0, run_id="r", type="stage"),
        Event(seq=2, ts=8.0, run_id="r", type="option.coded"),
        Event(seq=3, ts=16.0, run_id="r", type="option.smoke"),
        Event(seq=4, ts=24.0, run_id="r", type="universe.finished"),
    ]
    _ = [e async for e in replay_events(stream, speed=4.0)]
    assert sleeps == [0.15, 0.15, 1.5]


async def test_step_replanned_is_a_preparation_event(sleeps: list[float]) -> None:
    stream = [
        Event(seq=1, ts=0.0, run_id="r", type="option.smoke"),
        Event(seq=2, ts=8.0, run_id="r", type="step.replanned"),
        Event(seq=3, ts=16.0, run_id="r", type="universe.finished"),
    ]
    _ = [e async for e in replay_events(stream, speed=4.0)]
    assert sleeps == [0.15, 1.5]
