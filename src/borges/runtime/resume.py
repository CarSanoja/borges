from __future__ import annotations

from dataclasses import dataclass

from borges.runs.bus import EventBus
from borges.runs.events import Event, RunResumedData
from borges.runs.store import RunStore
from borges.runtime.context import RunContext
from borges.runtime.resume_log import replayable, rewind_events
from borges.runtime.universe_checkpoint import UNIVERSE_PREFIX, RestoredUniverses, load_restored


@dataclass
class ResumePlan:
    kept: list[Event]
    last_seq: int
    dropped: int
    restored: RestoredUniverses
    reason: str
    attempt: int

    @property
    def announced(self) -> bool:
        return any(e.type == "run.started" for e in self.kept)

    @property
    def replay(self) -> list[Event]:
        return replayable(self.kept)

    def event(self) -> dict[str, object]:
        return RunResumedData(
            reason=self.reason,
            attempt=self.attempt,
            restored_universes=len(self.restored.payloads),
            dropped_events=self.dropped,
        ).model_dump()


def plan_resume(store: RunStore, bus: EventBus, context: RunContext) -> ResumePlan:
    persisted = store.events(context.run_id)
    last_seq = max((e.seq for e in persisted), default=0)
    rows = context.checkpoints.with_prefix(context.run_id, UNIVERSE_PREFIX)
    restored = load_restored(rows)
    kept, dropped = rewind_events(store, context.run_id, restored)
    bus.reopen(context.run_id, kept)
    return ResumePlan(
        kept=kept,
        last_seq=last_seq,
        dropped=dropped,
        restored=restored,
        reason=context.resume_reason or "restart",
        attempt=context.attempt,
    )
