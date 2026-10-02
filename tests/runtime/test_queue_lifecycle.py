from __future__ import annotations

import pytest

from borges.runtime.db import RuntimeDb
from borges.runtime.jobs import CANCELLED, FAILED, QUEUED, RUNNING, SUCCEEDED
from borges.runtime.queue import JobQueue
from tests.runtime.conftest import allow_all, new_job

LEASE = 30.0


@pytest.fixture
def queue(db: RuntimeDb, clock) -> JobQueue:
    return JobQueue(db, clock)


def test_expired_lease_is_reclaimed_and_the_job_is_claimable_again(queue: JobQueue, clock) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w1", LEASE, allow_all)
    clock.advance(LEASE + 1)
    assert queue.running() == []
    requeued, exhausted = queue.reclaim_expired()
    assert (requeued, exhausted) == (["r1"], [])
    job = queue.get("r1")
    assert (job.state, job.resume_reason, job.lease_owner) == (QUEUED, "lease_expired", None)
    again = queue.claim("w2", LEASE, allow_all)
    assert again is not None and again.attempts == 2 and again.lease_owner == "w2"


def test_a_live_lease_is_not_reclaimed(queue: JobQueue, clock) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w1", LEASE, allow_all)
    clock.advance(LEASE - 1)
    assert queue.reclaim_expired() == ([], [])


def test_a_job_whose_attempts_are_spent_is_reported_exhausted(queue: JobQueue, clock) -> None:
    queue.submit(new_job("r1", max_attempts=1))
    queue.claim("w1", LEASE, allow_all)
    clock.advance(LEASE + 1)
    assert queue.reclaim_expired() == ([], ["r1"])


def test_stale_owner_cannot_finish_a_reclaimed_job(queue: JobQueue, clock) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w1", LEASE, allow_all)
    clock.advance(LEASE + 1)
    queue.reclaim_expired()
    queue.claim("w2", LEASE, allow_all)
    assert queue.finish("r1", "w1", SUCCEEDED) is False
    assert queue.get("r1").state == RUNNING


def test_release_returns_the_attempt(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    assert queue.release("r1", "w") is True
    job = queue.get("r1")
    assert (job.state, job.attempts, job.resume_reason) == (QUEUED, 0, "restart")


def test_retry_waits_for_its_backoff(queue: JobQueue, clock) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    assert queue.retry("r1", "w", "provider 503", 8.0) is True
    job = queue.get("r1")
    assert (job.state, job.last_error, job.resume_reason, job.attempts) == (
        QUEUED,
        "provider 503",
        "retry",
        1,
    )
    assert queue.claim("w", LEASE, allow_all) is None
    clock.advance(8)
    assert queue.claim("w", LEASE, allow_all).attempts == 2


def test_finish_requires_a_terminal_state(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    with pytest.raises(ValueError):
        queue.finish("r1", None, RUNNING)


def test_a_finished_job_stays_finished(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    assert queue.finish("r1", "w", SUCCEEDED) is True
    assert queue.finish("r1", "w", FAILED) is False
    assert queue.get("r1").state == SUCCEEDED


def test_cancelling_a_queued_job_ends_it_at_once(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    assert queue.request_cancel("r1") == "cancelled"
    assert queue.get("r1").state == CANCELLED
    assert queue.claim("w", LEASE, allow_all) is None


def test_cancelling_a_running_job_is_a_request_the_heartbeat_reports(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    assert queue.request_cancel("r1") == "requested"
    assert queue.heartbeat("r1", "w", LEASE).cancel is True


def test_cancel_of_unknown_and_finished_jobs(queue: JobQueue) -> None:
    assert queue.request_cancel("nope") == "unknown"
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    queue.finish("r1", "w", SUCCEEDED)
    assert queue.request_cancel("r1") == "finished"


def test_expire_leases_where_the_owner_is_dead(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    queue.submit(new_job("r2"))
    queue.claim("dead:1:a", LEASE, allow_all)
    queue.claim("alive:2:b", LEASE, allow_all)
    assert queue.expire_leases_where(lambda owner: owner.startswith("dead")) == 1
    assert queue.reclaim_expired() == (["r1"], [])
