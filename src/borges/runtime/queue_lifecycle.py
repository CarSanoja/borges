from __future__ import annotations

import time
from collections.abc import Callable, Collection

from borges.runtime.db import RuntimeDb
from borges.runtime.jobs import CANCELLED, QUEUED, RUNNING, TERMINAL_STATES, Job


class JobLifecycle:
    """How a claimed job leaves the running state: reclaim, release, retry, finish, cancel."""

    def __init__(self, db: RuntimeDb, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.clock = clock

    def reclaim_expired(self, skip: Collection[str] = ()) -> tuple[list[str], list[str]]:
        now = self.clock()
        requeued: list[str] = []
        exhausted: list[str] = []
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state = ? AND lease_expires <= ?", (RUNNING, now)
            ).fetchall()
            for row in rows:
                job = Job.from_row(row)
                if job.run_id in skip:
                    continue
                if job.attempts >= job.max_attempts:
                    exhausted.append(job.run_id)
                    continue
                self._release(conn, job.run_id, "lease_expired", "lease expired", now, 0)
                requeued.append(job.run_id)
        return requeued, exhausted

    def expire_leases_where(self, dead: Callable[[str], bool]) -> int:
        now = self.clock()
        count = 0
        with self.db.transaction() as conn:
            rows = conn.execute("SELECT run_id, lease_owner FROM jobs WHERE state = ?", (RUNNING,))
            for row in rows.fetchall():
                if row["lease_owner"] and dead(row["lease_owner"]):
                    conn.execute(
                        "UPDATE jobs SET lease_expires = ? WHERE run_id = ?",
                        (now - 1, row["run_id"]),
                    )
                    count += 1
        return count

    @staticmethod
    def _release(conn, run_id: str, reason: str, error: str | None, now: float, undo: int) -> None:
        conn.execute(
            "UPDATE jobs SET state = ?, lease_owner = NULL, lease_expires = NULL,"
            " attempts = MAX(0, attempts - ?), resume_reason = ?,"
            " last_error = COALESCE(?, last_error), not_before = ?, updated_at = ?"
            " WHERE run_id = ?",
            (QUEUED, undo, reason, error, now, now, run_id),
        )

    def release(self, run_id: str, owner: str, reason: str = "restart") -> bool:
        now = self.clock()
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT lease_owner FROM jobs WHERE run_id = ? AND state = ?", (run_id, RUNNING)
            ).fetchone()
            if row is None or row["lease_owner"] != owner:
                return False
            self._release(conn, run_id, reason, None, now, 1)
        return True

    def retry(self, run_id: str, owner: str, error: str, delay_s: float) -> bool:
        now = self.clock()
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT lease_owner FROM jobs WHERE run_id = ? AND state = ?", (run_id, RUNNING)
            ).fetchone()
            if row is None or row["lease_owner"] != owner:
                return False
            self._release(conn, run_id, "retry", error, now + delay_s, 0)
        return True

    def finish(self, run_id: str, owner: str | None, state: str, error: str | None = None) -> bool:
        if state not in TERMINAL_STATES:
            raise ValueError(f"not a terminal state: {state}")
        now = self.clock()
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None or row["state"] in TERMINAL_STATES:
                return False
            if owner is not None and row["lease_owner"] != owner:
                return False
            conn.execute(
                "UPDATE jobs SET state = ?, lease_owner = NULL, lease_expires = NULL,"
                " last_error = COALESCE(?, last_error), updated_at = ? WHERE run_id = ?",
                (state, error, now, run_id),
            )
        return True

    def request_cancel(self, run_id: str) -> str:
        now = self.clock()
        with self.db.transaction() as conn:
            row = conn.execute("SELECT state FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return "unknown"
            if row["state"] == QUEUED:
                conn.execute(
                    "UPDATE jobs SET state = ?, cancel_requested = 1, updated_at = ?"
                    " WHERE run_id = ?",
                    (CANCELLED, now, run_id),
                )
                return "cancelled"
            if row["state"] == RUNNING:
                conn.execute(
                    "UPDATE jobs SET cancel_requested = 1, updated_at = ? WHERE run_id = ?",
                    (now, run_id),
                )
                return "requested"
        return "finished"
