from __future__ import annotations

import pytest

from borges.runtime.dead_letter import DeadLetters
from borges.runtime.jobs import DEAD, QUEUED
from borges.runtime.queue import JobQueue
from tests.runtime.conftest import allow_all, new_job


@pytest.fixture
def parts(db, clock):
    return JobQueue(db, clock), DeadLetters(db, clock)


def test_a_buried_job_keeps_its_error_attempts_and_last_checkpoint(parts) -> None:
    queue, dead = parts
    queue.submit(new_job("r1"))
    queue.claim("w", 30, allow_all)
    checkpoint = {"key": "universe:u_1", "seq": 12, "checkpoints": 3}
    assert dead.bury("r1", "w", "Nebius 503", checkpoint) is True
    assert queue.get("r1").state == DEAD
    [entry] = dead.entries()
    assert (entry.run_id, entry.error, entry.attempts) == ("r1", "Nebius 503", 1)
    assert entry.last_checkpoint == checkpoint and entry.requeued_at is None
    assert entry.as_dict()["run_id"] == "r1"


def test_burying_needs_the_lease_owner(parts) -> None:
    queue, dead = parts
    queue.submit(new_job("r1"))
    queue.claim("w", 30, allow_all)
    assert dead.bury("r1", "someone-else", "x", None) is False
    assert dead.entries() == []


def test_burying_twice_is_a_noop(parts) -> None:
    queue, dead = parts
    queue.submit(new_job("r1"))
    queue.claim("w", 30, allow_all)
    assert dead.bury("r1", "w", "x", None) is True
    assert dead.bury("r1", None, "y", None) is False


def test_requeue_resets_attempts_and_hides_the_entry(parts) -> None:
    queue, dead = parts
    queue.submit(new_job("r1"))
    queue.claim("w", 30, allow_all)
    dead.bury("r1", "w", "x", None)
    job = dead.requeue("r1")
    assert job is not None
    assert (job.state, job.attempts, job.resume_reason) == (QUEUED, 0, "requeue")
    assert dead.entries() == []
    assert [e.run_id for e in dead.entries(include_requeued=True)] == ["r1"]
    assert queue.claim("w2", 30, allow_all).run_id == "r1"


def test_requeue_refuses_jobs_that_are_not_dead_or_failed(parts) -> None:
    queue, dead = parts
    queue.submit(new_job("r1"))
    assert dead.requeue("r1") is None
    assert dead.requeue("missing") is None
