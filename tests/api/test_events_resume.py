from __future__ import annotations

import pytest

from tests.api.test_routes_runs import Env, FakeBus


@pytest.fixture
def env(tmp_path) -> Env:
    return Env(tmp_path, key=None)


class RecordingBus(FakeBus):
    def __init__(self) -> None:
        self.from_seqs: list[int] = []

    async def subscribe(self, run_id: str, from_seq: int):
        self.from_seqs.append(from_seq)
        async for event in super().subscribe(run_id, from_seq):
            yield event


async def fetch(env: Env, url: str, headers: dict) -> list[int]:
    bus = RecordingBus()
    env.app.state.bus = bus
    async with env.client() as client:
        response = await client.get(url, headers=headers)
    assert response.status_code == 200
    return bus.from_seqs


async def test_last_event_id_resumes_after_that_seq(env: Env) -> None:
    assert await fetch(env, "/api/runs/r1/events", {"Last-Event-ID": "60"}) == [60]


async def test_last_event_id_never_lowers_from_seq(env: Env) -> None:
    seqs = await fetch(env, "/api/runs/r1/events?from_seq=80", {"Last-Event-ID": "60"})
    assert seqs == [80]


async def test_garbage_last_event_id_is_ignored(env: Env) -> None:
    assert await fetch(env, "/api/runs/r1/events", {"Last-Event-ID": "abc"}) == [0]


async def test_unicode_and_oversized_last_event_id_are_ignored(env: Env) -> None:
    assert await fetch(env, "/api/runs/r1/events", {"Last-Event-ID": "1" * 5000}) == [0]
    assert await fetch(env, "/api/runs/r1/events", {"Last-Event-ID": "\xb2".encode("latin-1")}) == [
        0
    ]


async def test_events_stream_to_run_finished(env: Env) -> None:
    async with env.client() as client:
        response = await client.get("/api/runs/r1/events?from_seq=1")
        missing = await client.get("/api/runs/nope/events")
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "id: 1" in response.text
    assert "id: 0" not in response.text
    assert "event: run.finished" in response.text
    assert missing.status_code == 404


async def test_universe_404(env: Env) -> None:
    async with env.client() as client:
        assert (await client.get("/api/runs/r1/universes/u9")).status_code == 404
        assert (await client.get("/api/runs/nope/universes/u9")).status_code == 404
