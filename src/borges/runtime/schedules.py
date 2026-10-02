from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from borges.identity.api_key import parse_duration
from borges.runtime.db import RuntimeDb

MIN_EVERY_S = 60.0


@dataclass(frozen=True)
class Schedule:
    id: str
    case_id: str
    llm: str | None
    every_s: float
    principal: str
    next_run: float
    enabled: bool
    created_at: float
    last_run_id: str | None
    last_run_at: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "llm": self.llm,
            "every_s": self.every_s,
            "principal": self.principal,
            "next_run": self.next_run,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_run_id": self.last_run_id,
            "last_run_at": self.last_run_at,
        }


def parse_every(raw: str) -> float:
    seconds = parse_duration(raw)
    if seconds is None:
        raise ValueError("--every needs a duration such as 24h, 90m or 7d")
    if seconds < MIN_EVERY_S:
        raise ValueError(f"--every must be at least {int(MIN_EVERY_S)}s")
    return seconds


def _schedule(row: Any) -> Schedule:
    return Schedule(
        id=row["id"],
        case_id=row["case_id"],
        llm=row["llm"],
        every_s=row["every_s"],
        principal=row["principal"],
        next_run=row["next_run"],
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
        last_run_id=row["last_run_id"],
        last_run_at=row["last_run_at"],
    )


class ScheduleStore:
    def __init__(self, db: RuntimeDb, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.clock = clock

    def add(
        self,
        case_id: str,
        every_s: float,
        principal: str,
        llm: str | None = None,
        first_in_s: float | None = None,
    ) -> Schedule:
        now = self.clock()
        schedule_id = "sch_" + secrets.token_hex(4)
        first = now + (every_s if first_in_s is None else first_in_s)
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO schedules (id, case_id, llm, every_s, principal, next_run,"
                " created_at) VALUES (?,?,?,?,?,?,?)",
                (schedule_id, case_id, llm, every_s, principal, first, now),
            )
        found = self.get(schedule_id)
        assert found is not None
        return found

    def get(self, schedule_id: str) -> Schedule | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        return _schedule(row) if row else None

    def entries(self) -> list[Schedule]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM schedules ORDER BY created_at").fetchall()
        return [_schedule(r) for r in rows]

    def remove(self, schedule_id: str) -> bool:
        with self.db.transaction() as conn:
            return conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,)).rowcount > 0

    def due(self) -> list[Schedule]:
        now = self.clock()
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM schedules WHERE enabled = 1 AND next_run <= ? ORDER BY next_run",
                (now,),
            ).fetchall()
        return [_schedule(r) for r in rows]

    def advance(self, schedule: Schedule, run_id: str | None) -> None:
        now = self.clock()
        following = schedule.next_run + schedule.every_s
        while following <= now:
            following += schedule.every_s
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE schedules SET next_run = ?, last_run_id = COALESCE(?, last_run_id),"
                " last_run_at = CASE WHEN ? IS NULL THEN last_run_at ELSE ? END WHERE id = ?",
                (following, run_id, run_id, now, schedule.id),
            )
