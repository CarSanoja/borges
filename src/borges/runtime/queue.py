from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from borges.runtime.jobs import (
    CANCELLED,
    DEAD,
    FAILED,
    QUEUED,
    RUNNING,
    Job,
    NewJob,
    SubmitResult,
)
from borges.runtime.queue_lifecycle import JobLifecycle

Admit = Callable[[Job, list[Job]], bool]
REUSABLE_AFTER_FAILURE = frozenset({FAILED, CANCELLED, DEAD})


@dataclass(frozen=True)
class IdempotencyKey:
    key: str
    derived: bool
    window_s: float


@dataclass(frozen=True)
class Heartbeat:
    held: bool
    cancel: bool


class JobQueue(JobLifecycle):
    """Durable job queue: submit with an idempotency key, claim with a lease, renew by heartbeat."""

    def get(self, run_id: str) -> Job | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
        return Job.from_row(row) if row else None

    def lookup(self, idem: IdempotencyKey) -> str | None:
        with self.db.connect() as conn:
            return self._existing(conn, idem, self.clock())

    def _existing(self, conn, idem: IdempotencyKey, now: float) -> str | None:
        row = conn.execute(
            "SELECT run_id FROM idempotency WHERE key = ? AND expires_at > ?", (idem.key, now)
        ).fetchone()
        if row is None:
            return None
        job = conn.execute("SELECT state FROM jobs WHERE run_id = ?", (row["run_id"],)).fetchone()
        if job is None:
            return None
        if idem.derived and job["state"] in REUSABLE_AFTER_FAILURE:
            return None
        return row["run_id"]

    def submit(self, new: NewJob, idem: IdempotencyKey | None = None) -> SubmitResult:
        now = self.clock()
        with self.db.transaction() as conn:
            if idem is not None:
                found = self._existing(conn, idem, now)
                if found is not None:
                    return SubmitResult(found, False)
            conn.execute(
                "INSERT INTO jobs (run_id, state, principal, owner_key, anonymous, live, source,"
                " schedule_id, request, upload_id, dataset_name, max_attempts, not_before,"
                " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    new.run_id,
                    QUEUED,
                    new.principal,
                    new.owner_key,
                    int(new.anonymous),
                    int(new.live),
                    new.source,
                    new.schedule_id,
                    new.request,
                    new.upload_id,
                    new.dataset_name,
                    new.max_attempts,
                    now,
                    now,
                    now,
                ),
            )
            if idem is not None:
                conn.execute(
                    "INSERT OR REPLACE INTO idempotency (key, run_id, derived, created_at,"
                    " expires_at) VALUES (?,?,?,?,?)",
                    (idem.key, new.run_id, int(idem.derived), now, now + idem.window_s),
                )
        return SubmitResult(new.run_id, True)

    def running(self) -> list[Job]:
        with self.db.connect() as conn:
            return self._running(conn, self.clock())

    def _running(self, conn, now: float) -> list[Job]:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE state = ? AND lease_expires > ?", (RUNNING, now)
        ).fetchall()
        return [Job.from_row(r) for r in rows]

    def claim(self, owner: str, lease_s: float, admit: Admit) -> Job | None:
        now = self.clock()
        with self.db.transaction() as conn:
            running = self._running(conn, now)
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state = ? AND not_before <= ? ORDER BY created_at",
                (QUEUED, now),
            ).fetchall()
            for row in rows:
                job = Job.from_row(row)
                if not admit(job, running):
                    continue
                conn.execute(
                    "UPDATE jobs SET state = ?, lease_owner = ?, lease_expires = ?,"
                    " attempts = attempts + 1, updated_at = ? WHERE run_id = ?",
                    (RUNNING, owner, now + lease_s, now, job.run_id),
                )
                claimed = conn.execute(
                    "SELECT * FROM jobs WHERE run_id = ?", (job.run_id,)
                ).fetchone()
                return Job.from_row(claimed)
        return None

    def heartbeat(self, run_id: str, owner: str, lease_s: float) -> Heartbeat:
        now = self.clock()
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "UPDATE jobs SET lease_expires = ?, updated_at = ? WHERE run_id = ?"
                " AND lease_owner = ? AND state = ?",
                (now + lease_s, now, run_id, owner, RUNNING),
            )
            if cursor.rowcount == 0:
                return Heartbeat(False, False)
            row = conn.execute(
                "SELECT cancel_requested FROM jobs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return Heartbeat(True, bool(row["cancel_requested"]))

    def active_run_ids(self) -> set[str]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT run_id FROM jobs WHERE state IN (?, ?)", (QUEUED, RUNNING)
            ).fetchall()
        return {r["run_id"] for r in rows}

    def stats(self) -> dict[str, float | int | None]:
        now = self.clock()
        with self.db.connect() as conn:
            depth = conn.execute(
                "SELECT COUNT(*) AS n, MIN(created_at) AS oldest FROM jobs WHERE state = ?",
                (QUEUED,),
            ).fetchone()
            workers = len(self._running(conn, now))
            dead = conn.execute(
                "SELECT COUNT(*) AS n FROM dead_letter WHERE requeued_at IS NULL"
            ).fetchone()
        oldest = depth["oldest"]
        return {
            "queue_depth": depth["n"],
            "active_workers": workers,
            "oldest_job_age_s": round(now - oldest, 3) if oldest is not None else None,
            "dead_letter_count": dead["n"],
        }
