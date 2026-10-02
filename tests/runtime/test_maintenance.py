from __future__ import annotations

import asyncio
import os
import socket

from borges.runtime.maintenance import drain_queue, owner_is_dead
from borges.runtime.queue import JobQueue
from tests.runtime.conftest import new_job


def test_owner_liveness_is_only_judged_for_this_host() -> None:

    host = socket.gethostname()
    assert owner_is_dead(f"{host}:999999:t") is True
    assert owner_is_dead(f"{host}:{os.getpid()}:t") is False
    assert owner_is_dead("other-host:999999:t") is False
    assert owner_is_dead("garbage") is False


async def test_drain_returns_true_once_the_queue_is_empty(db, clock) -> None:
    queue = JobQueue(db, clock)
    changed = asyncio.Event()
    assert await drain_queue(queue, changed, 1.0) is True


async def test_drain_gives_up_at_the_deadline(db, clock) -> None:
    queue = JobQueue(db, clock)
    queue.submit(new_job("r1"))
    assert await drain_queue(queue, asyncio.Event(), 0.1) is False


async def test_drain_wakes_when_the_queue_changes(db, clock) -> None:
    queue = JobQueue(db, clock)
    queue.submit(new_job("r1"))
    changed = asyncio.Event()
    task = asyncio.create_task(drain_queue(queue, changed, 5.0))
    await asyncio.sleep(0.05)
    queue.request_cancel("r1")
    changed.set()
    assert await task is True
