from __future__ import annotations

from borges.runtime.db import RuntimeDb
from borges.runtime.jobs import ACTIVE_STATES, QUEUED, TERMINAL_STATES, Job
from borges.runtime.queue import JobQueue
from tests.runtime.conftest import new_job


def test_job_rows_map_to_dataclasses(db: RuntimeDb, clock) -> None:
    queue = JobQueue(db, clock)
    queue.submit(new_job("r1", live=True, upload_id="u1", dataset_name="d.csv"))
    job = queue.get("r1")
    assert isinstance(job, Job)
    assert (job.state, job.live, job.anonymous, job.upload_id) == (QUEUED, True, True, "u1")
    assert job.attempts == 0 and job.cancel_requested is False and job.lease_owner is None


def test_state_groups_do_not_overlap() -> None:
    assert not ACTIVE_STATES & TERMINAL_STATES
