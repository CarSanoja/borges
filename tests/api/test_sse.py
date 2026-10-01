from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
from fastapi import FastAPI

from borges.api.sse import event_to_sse, sse_response
from borges.runs.events import Event


def make_event(seq: int, type_: str = "stage") -> Event:
    return Event(seq=seq, ts=1.0, run_id="r1", type=type_, data={"n": seq})


async def stream(events: list[Event]) -> AsyncIterator[Event]:
    for event in events:
        yield event


def test_event_to_sse_maps_type_seq_and_json() -> None:
    message = event_to_sse(make_event(3, "plan.ready"))
    assert message["event"] == "plan.ready"
    assert message["id"] == "3"
    assert json.loads(message["data"])["seq"] == 3


async def test_stream_ends_after_terminal_event() -> None:
    app = FastAPI()
    events = [
        make_event(0),
        make_event(1, "run.finished"),
        make_event(2),
    ]

    @app.get("/s")
    async def s():
        return sse_response(stream(events))

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        response = await client.get("/s")
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: stage" in response.text
    assert "event: run.finished" in response.text
    assert '"seq":2' not in response.text.replace(" ", "")
