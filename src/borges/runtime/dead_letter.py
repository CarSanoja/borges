from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from borges.runtime.db import RuntimeDb
from borges.runtime.jobs import DEAD, FAILED, QUEUED, Job


@dataclass(frozen=True)
class DeadLetter:
    run_id: str
    error: str
    attempts: int
    last_checkpoint: dict[str, Any] | None
    created_at: float
    requeued_at: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "error": self.error,
            "attempts": self.attempts,
            "last_checkpoint": self.last_checkpoint,
            "created_at": self.created_at,
            "requeued_at": self.requeued_at,
        }


class DeadLetters:
    def __init__(self, db: RuntimeDb, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.clock = clock

    def bury(
        self, run_id: str, owner: str | None, error: str, last_checkpoint: dict[str, Any] | None
    ) -> bool:
        now = self.clock()
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None or row["state"] == DEAD:
                return False
            if owner is not None and row["lease_owner"] != owner:
                return False
            conn.execute(
                "UPDATE jobs SET state = ?, lease_owner = NULL, lease_expires = NULL,"
                " last_error = ?, updated_at = ? WHERE run_id = ?",
                (DEAD, error, now, run_id),
            )
            conn.execute(
                "INSERT OR REPLACE INTO dead_letter (run_id, error, attempts, last_checkpoint,"
                " request, created_at, requeued_at) VALUES (?,?,?,?,?,?,NULL)",
                (
                    run_id,
                    error,
                    row["attempts"],
                    json.dumps(last_checkpoint) if last_checkpoint else None,
                    row["request"],
                    now,
                ),
            )
        return True

    def entries(self, include_requeued: bool = False) -> list[DeadLetter]:
        query = "SELECT * FROM dead_letter"
        if not include_requeued:
            query += " WHERE requeued_at IS NULL"
        with self.db.connect() as conn:
            rows = conn.execute(query + " ORDER BY created_at DESC").fetchall()
        return [
            DeadLetter(
                r["run_id"],
                r["error"],
                r["attempts"],
                json.loads(r["last_checkpoint"]) if r["last_checkpoint"] else None,
                r["created_at"],
                r["requeued_at"],
            )
            for r in rows
        ]

    def requeue(self, run_id: str) -> Job | None:
        now = self.clock()
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None or row["state"] not in (DEAD, FAILED):
                return None
            conn.execute(
                "UPDATE jobs SET state = ?, attempts = 0, cancel_requested = 0, not_before = ?,"
                " resume_reason = 'requeue', lease_owner = NULL, lease_expires = NULL,"
                " updated_at = ? WHERE run_id = ?",
                (QUEUED, now, now, run_id),
            )
            conn.execute("UPDATE dead_letter SET requeued_at = ? WHERE run_id = ?", (now, run_id))
            updated = conn.execute("SELECT * FROM jobs WHERE run_id = ?", (run_id,)).fetchone()
        return Job.from_row(updated)
