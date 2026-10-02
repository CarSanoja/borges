from __future__ import annotations

import contextlib
import json
import time
from collections import Counter
from collections.abc import Callable
from typing import Any, cast

from borges.armor.pii_deep import redact_deep
from borges.llm.client import UsageTotals
from borges.runs.bus import EventBus
from borges.runs.events import Event, EventType, UsageData
from borges.runs.store import RunStore
from borges.telemetry.event_audit import audit_run_event

UsageProbe = Callable[[], tuple[UsageTotals, int]]
USAGE_EVERY_UNIVERSES = 5


def replay_key(event_type: str, data: dict[str, Any]) -> str:
    return event_type + json.dumps(data, sort_keys=True, default=str)


class RunEmitter:
    """Single writer of a run's events: assigns seq and ts, persists, then publishes.

    A resumed run passes the events already persisted; re-running the deterministic stages
    emits the same events again, and those are swallowed instead of being written twice.
    """

    def __init__(
        self,
        run_id: str,
        store: RunStore,
        bus: EventBus,
        replay: list[Event] | None = None,
        last_seq: int = 0,
    ) -> None:
        self.run_id = run_id
        self.store = store
        self.bus = bus
        self.seq = last_seq
        self.universes_finished = 0
        self.usage_probe: UsageProbe | None = None
        self._pending: Counter[str] = Counter(replay_key(e.type, e.data) for e in replay or [])

    def has_pending(self, event_type: str, data: dict[str, Any]) -> bool:
        return self._pending[replay_key(event_type, redact_deep(data))] > 0

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        raw = data
        data = redact_deep(data)
        key = replay_key(event_type, data)
        if self._pending[key] > 0:
            self._pending[key] -= 1
            return
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
        with contextlib.suppress(Exception):
            audit_run_event(event_type, raw)
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
