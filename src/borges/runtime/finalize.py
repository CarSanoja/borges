from __future__ import annotations

import time

from borges.runs.bus import EventBus
from borges.runs.events import Event
from borges.runs.store import RunStore


def append_terminal(
    store: RunStore, bus: EventBus, run_id: str, status: str, reason: str | None = None
) -> None:
    """Close a run that has no worker: append its terminal events and set the meta status."""
    if not store.exists(run_id):
        return
    events = store.events(run_id)
    if any(e.type in ("run.finished", "run.failed") for e in events):
        store.update_meta(run_id, status=status)
        return
    seq = max((e.seq for e in events), default=0)
    now = time.time()
    first = (
        ("run.cancelled", {"reason": reason or "cancelled"})
        if status == "cancelled"
        else ("run.failed", {"error": reason or "failed"})
    )
    for kind, data in (first, ("run.finished", {"status": status, "elapsed_s": 0.0})):
        seq += 1
        event = Event(seq=seq, ts=now, run_id=run_id, type=kind, data=data)  # type: ignore[arg-type]
        store.append(event)
        bus.publish(event)
    store.update_meta(run_id, status=status)
    bus.close(run_id)
