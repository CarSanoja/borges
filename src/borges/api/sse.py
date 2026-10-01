from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sse_starlette.sse import EventSourceResponse

from borges.runs.events import Event

TERMINAL_TYPES = frozenset({"run.finished", "run.failed"})
PING_SECONDS = 15


def event_to_sse(event: Event) -> dict[str, Any]:
    return {
        "event": event.type,
        "id": str(event.seq),
        "data": event.model_dump_json(),
    }


async def _sse_messages(events: AsyncIterator[Event]) -> AsyncIterator[dict[str, Any]]:
    async for event in events:
        yield event_to_sse(event)
        if event.type in TERMINAL_TYPES:
            return


def sse_response(events: AsyncIterator[Event]) -> EventSourceResponse:
    """Stream events as server-sent events, closing after a terminal event."""
    return EventSourceResponse(
        _sse_messages(events),
        ping=PING_SECONDS,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
