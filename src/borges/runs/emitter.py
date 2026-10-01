from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, cast

from borges.llm.client import UsageTotals
from borges.runs.bus import EventBus
from borges.runs.events import Event, EventType, UsageData
from borges.runs.store import RunStore

UsageProbe = Callable[[], tuple[UsageTotals, int]]
USAGE_EVERY_UNIVERSES = 5


class RunEmitter:
    """Single writer of a run's events: assigns seq and ts, persists, then publishes."""

    def __init__(self, run_id: str, store: RunStore, bus: EventBus) -> None:
        self.run_id = run_id
        self.store = store
        self.bus = bus
        self.seq = 0
        self.universes_finished = 0
        self.usage_probe: UsageProbe | None = None

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        self.seq += 1
        event = Event(
            seq=self.seq,
            ts=time.time(),
            run_id=self.run_id,
            type=cast(EventType, event_type),
            data=data,
        )
        self.store.append(event)
        self.bus.publish(event)
        if event_type == "universe.finished":
            self.universes_finished += 1
            if self.universes_finished % USAGE_EVERY_UNIVERSES == 0:
                await self.usage()

    async def stage(self, name: str, status: str, detail: str = "") -> None:
        await self.emit("stage", {"name": name, "status": status, "detail": detail})

    async def usage(self) -> None:
        if self.usage_probe is None:
            return
        totals, checkpoints = self.usage_probe()
        payload = UsageData(
            tokens_in=totals.tokens_in,
            tokens_out=totals.tokens_out,
            cost_usd=totals.cost_usd,
            llm_calls=totals.calls,
            cached_calls=totals.cached_calls,
            checkpoints=checkpoints,
            universes=self.universes_finished,
        )
        await self.emit("usage", payload.model_dump(mode="json"))
