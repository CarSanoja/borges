from __future__ import annotations

import sqlite3
from dataclasses import dataclass

QUEUED = "queued"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"
CANCELLED = "cancelled"
DEAD = "dead"

TERMINAL_STATES = frozenset({SUCCEEDED, FAILED, CANCELLED, DEAD})
ACTIVE_STATES = frozenset({QUEUED, RUNNING})


@dataclass(frozen=True)
class Job:
    run_id: str
    state: str
    principal: str
    owner_key: str
    anonymous: bool
    live: bool
    source: str
    schedule_id: str | None
    request: str
    upload_id: str | None
    dataset_name: str | None
    attempts: int
    max_attempts: int
    not_before: float
    lease_owner: str | None
    lease_expires: float | None
    cancel_requested: bool
    resume_reason: str | None
    last_error: str | None
    created_at: float
    updated_at: float

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Job:
        return cls(
            run_id=row["run_id"],
            state=row["state"],
            principal=row["principal"],
            owner_key=row["owner_key"],
            anonymous=bool(row["anonymous"]),
            live=bool(row["live"]),
            source=row["source"],
            schedule_id=row["schedule_id"],
            request=row["request"],
            upload_id=row["upload_id"],
            dataset_name=row["dataset_name"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            not_before=row["not_before"],
            lease_owner=row["lease_owner"],
            lease_expires=row["lease_expires"],
            cancel_requested=bool(row["cancel_requested"]),
            resume_reason=row["resume_reason"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True)
class NewJob:
    run_id: str
    principal: str
    owner_key: str
    anonymous: bool
    live: bool
    request: str
    max_attempts: int
    source: str = "api"
    schedule_id: str | None = None
    upload_id: str | None = None
    dataset_name: str | None = None


@dataclass(frozen=True)
class SubmitResult:
    run_id: str
    created: bool
