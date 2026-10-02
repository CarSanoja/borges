from __future__ import annotations

import pytest

from borges.runtime.db import RuntimeDb
from borges.runtime.jobs import DEAD, FAILED, QUEUED, RUNNING
from borges.runtime.queue import IdempotencyKey, JobQueue
from tests.runtime.conftest import allow_all, new_job

LEASE = 30.0


@pytest.fixture
def queue(db: RuntimeDb, clock) -> JobQueue:
    return JobQueue(db, clock)


def test_duplicate_submission_returns_the_existing_run(queue: JobQueue) -> None:
    key = IdempotencyKey("k", False, 600)
    first = queue.submit(new_job("r1"), key)
    second = queue.submit(new_job("r2"), key)
    assert (first.run_id, first.created) == ("r1", True)
    assert (second.run_id, second.created) == ("r1", False)
    assert queue.get("r2") is None


def test_idempotency_key_expires_with_its_window(queue: JobQueue, clock) -> None:
    key = IdempotencyKey("k", True, 600)
    queue.submit(new_job("r1"), key)
    clock.advance(601)
    again = queue.submit(new_job("r2"), key)
    assert (again.run_id, again.created) == ("r2", True)


def test_derived_key_is_not_reused_after_a_failure(queue: JobQueue) -> None:
    key = IdempotencyKey("k", True, 600)
    queue.submit(new_job("r1"), key)
    queue.claim("w", LEASE, allow_all)
    queue.finish("r1", "w", FAILED, "boom")
    assert queue.submit(new_job("r2"), key).created is True


def test_explicit_key_is_reused_even_after_a_failure(queue: JobQueue) -> None:
    key = IdempotencyKey("k", False, 600)
    queue.submit(new_job("r1"), key)
    queue.claim("w", LEASE, allow_all)
    queue.finish("r1", "w", FAILED, "boom")
    assert queue.submit(new_job("r2"), key).run_id == "r1"


def test_lookup_finds_a_live_key(queue: JobQueue) -> None:
    key = IdempotencyKey("k", False, 600)
    assert queue.lookup(key) is None
    queue.submit(new_job("r1"), key)
    assert queue.lookup(key) == "r1"


def test_claim_takes_the_oldest_job_and_counts_the_attempt(queue: JobQueue, clock) -> None:
    queue.submit(new_job("old"))
    clock.advance(1)
    queue.submit(new_job("new"))
    job = queue.claim("w1", LEASE, allow_all)
    assert job is not None and job.run_id == "old"
    assert (job.state, job.attempts, job.lease_owner) == (RUNNING, 1, "w1")
    assert job.lease_expires == pytest.approx(clock.now + LEASE)


def test_claim_returns_none_when_nothing_is_queued(queue: JobQueue) -> None:
    assert queue.claim("w", LEASE, allow_all) is None


def test_a_job_is_claimed_once(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    assert queue.claim("w1", LEASE, allow_all) is not None
    assert queue.claim("w2", LEASE, allow_all) is None


def test_admission_can_leave_a_job_queued(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    assert queue.claim("w", LEASE, lambda job, running: False) is None
    assert queue.get("r1").state == QUEUED


def test_admission_sees_the_running_jobs(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    queue.submit(new_job("r2"))
    seen: list[int] = []

    def admit(job, running) -> bool:
        seen.append(len(running))
        return True

    queue.claim("w", LEASE, admit)
    queue.claim("w", LEASE, admit)
    assert seen == [0, 1]


def test_claim_skips_a_blocked_job_for_a_later_admissible_one(queue: JobQueue, clock) -> None:
    queue.submit(new_job("blocked"))
    clock.advance(1)
    queue.submit(new_job("free"))
    job = queue.claim("w", LEASE, lambda job, running: job.run_id == "free")
    assert job is not None and job.run_id == "free"


def test_heartbeat_renews_the_lease(queue: JobQueue, clock) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    clock.advance(20)
    beat = queue.heartbeat("r1", "w", LEASE)
    assert (beat.held, beat.cancel) == (True, False)
    assert queue.get("r1").lease_expires == pytest.approx(clock.now + LEASE)


def test_heartbeat_by_another_owner_does_not_hold_the_lease(queue: JobQueue) -> None:
    queue.submit(new_job("r1"))
    queue.claim("w", LEASE, allow_all)
    assert queue.heartbeat("r1", "intruder", LEASE).held is False


def test_active_run_ids_cover_queued_and_running(queue: JobQueue) -> None:
    for run_id in ("r1", "r2", "r3"):
        queue.submit(new_job(run_id))
    queue.claim("w", LEASE, allow_all)
    queue.request_cancel("r3")
    assert queue.active_run_ids() == {"r1", "r2"}


def test_stats_report_depth_workers_age_and_dead_letters(queue: JobQueue, clock, db) -> None:
    assert queue.stats() == {
        "queue_depth": 0,
        "active_workers": 0,
        "oldest_job_age_s": None,
        "dead_letter_count": 0,
    }
    queue.submit(new_job("r1"))
    clock.advance(5)
    queue.submit(new_job("r2"))
    queue.claim("w", LEASE, allow_all)
    clock.advance(10)
    stats = queue.stats()
    assert stats["queue_depth"] == 1 and stats["active_workers"] == 1
    assert stats["oldest_job_age_s"] == pytest.approx(10.0)
    assert DEAD == "dead"
