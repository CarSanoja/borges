from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from borges.runs.events import Event
from borges.runs.store import RunStore

TERMINAL_TYPES = frozenset({"run.finished", "run.failed"})


def _interrupted(run_id: str, seq: int) -> Event:
    return Event(
        seq=seq,
        ts=time.time(),
        run_id=run_id,
        type="run.failed",
        data={"error": "the run ended without a final event"},
    )


@dataclass
class _Channel:
    history: list[Event] = field(default_factory=list)
    queues: set[asyncio.Queue[Event]] = field(default_factory=set)


class EventBus:
    """Fan-out of run events. Live runs are served from memory, finished runs from the store."""

    def __init__(self, store: RunStore) -> None:
        self.store = store
        self._channels: dict[str, _Channel] = {}

    def open(self, run_id: str) -> None:
        self._channels.setdefault(run_id, _Channel())

    def reopen(self, run_id: str, history: list[Event]) -> None:
        channel = self._channels.setdefault(run_id, _Channel())
        channel.history = list(history)

    def is_live(self, run_id: str) -> bool:
        return run_id in self._channels

    def publish(self, event: Event) -> None:
        channel = self._channels.get(event.run_id)
        if channel is None:
            return
        channel.history.append(event)
        for queue in channel.queues:
            queue.put_nowait(event)
        if event.type == "run.finished":
            self._channels.pop(event.run_id, None)

    def close(self, run_id: str) -> None:
        channel = self._channels.pop(run_id, None)
        if channel is None or any(e.type in TERMINAL_TYPES for e in channel.history):
            return
        last = channel.history[-1].seq if channel.history else 0
        for queue in channel.queues:
            queue.put_nowait(_interrupted(run_id, last + 1))

    async def subscribe(self, run_id: str, from_seq: int = 0) -> AsyncIterator[Event]:
        channel = self._channels.get(run_id)
        if channel is None:
            last = 0
            for event in self.store.events(run_id):
                last = max(last, event.seq)
                if event.seq > from_seq:
                    yield event
                if event.type in TERMINAL_TYPES:
                    return
            yield _interrupted(run_id, last + 1)
            return
        queue: asyncio.Queue[Event] = asyncio.Queue()
        backlog = [e for e in channel.history if e.seq > from_seq]
        channel.queues.add(queue)
        try:
            for event in backlog:
                yield event
                if event.type in TERMINAL_TYPES:
                    return
            last_seq = backlog[-1].seq if backlog else from_seq
            while True:
                event = await queue.get()
                if event.seq <= last_seq:
                    continue
                last_seq = event.seq
                yield event
                if event.type in TERMINAL_TYPES:
                    return
        finally:
            channel.queues.discard(queue)
