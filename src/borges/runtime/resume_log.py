from __future__ import annotations

from borges.runs.events import Event
from borges.runs.store import RunStore
from borges.runtime.universe_checkpoint import RestoredUniverses

TERMINAL = frozenset({"run.finished", "run.failed", "run.cancelled"})
UNIVERSE_EVENTS = frozenset({"universe.started", "universe.finished"})
NEVER_REPLAYED = frozenset(
    {
        "usage",
        "universe.started",
        "universe.finished",
        "checkpoint.created",
        "run.started",
        "run.resumed",
        "run.finished",
        "run.failed",
        "run.cancelled",
    }
)


def _keep(event: Event, restored: RestoredUniverses, reachable: set[str]) -> bool:
    if event.type in TERMINAL:
        return False
    if event.type in UNIVERSE_EVENTS:
        return event.data.get("universe", {}).get("id") in restored.ids
    if event.type == "checkpoint.created":
        return event.data.get("checkpoint_id") in reachable
    return True


def rewind_events(
    store: RunStore, run_id: str, restored: RestoredUniverses
) -> tuple[list[Event], int]:
    events = store.events(run_id)
    reachable = restored.checkpoint_ids()
    kept = [e for e in events if _keep(e, restored, reachable)]
    if len(kept) != len(events):
        store.replace_events(run_id, kept)
    return kept, len(events) - len(kept)


def replayable(events: list[Event]) -> list[Event]:
    return [e for e in events if e.type not in NEVER_REPLAYED]
