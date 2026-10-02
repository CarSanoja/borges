from __future__ import annotations

import asyncio
import contextlib
import socket
from typing import TYPE_CHECKING

from borges.runs.ownership import pid_alive
from borges.runtime.finalize import append_terminal
from borges.runtime.queue import JobQueue

if TYPE_CHECKING:
    from borges.runtime.runtime import Runtime

LEASE_EXHAUSTED = "the worker lease expired on every attempt"
DRAIN_POLL_S = 0.25


def owner_is_dead(owner: str) -> bool:
    host, _, rest = owner.partition(":")
    pid, _, _ = rest.partition(":")
    return host == socket.gethostname() and pid.isdigit() and not pid_alive(int(pid))


def reclaim(runtime: Runtime) -> None:
    requeued, exhausted = runtime.queue.reclaim_expired()
    for run_id in requeued:
        if runtime.store.exists(run_id):
            runtime.store.update_meta(run_id, status="queued")
    for run_id in exhausted:
        append_terminal(runtime.store, runtime.bus, run_id, "failed", LEASE_EXHAUSTED)
        runtime.dead.bury(run_id, None, LEASE_EXHAUSTED, runtime.checkpoints.last(run_id))


async def drain_queue(queue: JobQueue, changed: asyncio.Event, wait_s: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + wait_s
    while queue.active_run_ids():
        remaining = deadline - loop.time()
        if remaining <= 0:
            return False
        changed.clear()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(changed.wait(), min(remaining, DRAIN_POLL_S))
    return True
