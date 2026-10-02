from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from borges.config import Settings

DB_RELATIVE = Path("runtime") / "runtime.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    principal TEXT NOT NULL,
    owner_key TEXT NOT NULL,
    anonymous INTEGER NOT NULL DEFAULT 1,
    live INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'api',
    schedule_id TEXT,
    request TEXT NOT NULL,
    upload_id TEXT,
    dataset_name TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    not_before REAL NOT NULL DEFAULT 0,
    lease_owner TEXT,
    lease_expires REAL,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    resume_reason TEXT,
    last_error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_state ON jobs (state, not_before, created_at);
CREATE TABLE IF NOT EXISTS idempotency (
    key TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    derived INTEGER NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS dead_letter (
    run_id TEXT PRIMARY KEY,
    error TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    last_checkpoint TEXT,
    request TEXT NOT NULL,
    created_at REAL NOT NULL,
    requeued_at REAL
);
CREATE TABLE IF NOT EXISTS checkpoints (
    run_id TEXT NOT NULL,
    key TEXT NOT NULL,
    seq INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (run_id, key)
);
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    llm TEXT,
    every_s REAL NOT NULL,
    principal TEXT NOT NULL,
    next_run REAL NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    last_run_id TEXT,
    last_run_at REAL
);
"""


def runtime_db_path(settings: Settings) -> Path:
    return Path(settings.borges_home) / DB_RELATIVE


class RuntimeDb:
    """SQLite in WAL mode; every operation opens a short-lived connection."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def _open(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = self._open()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")


def open_runtime_db(settings: Settings) -> RuntimeDb:
    return RuntimeDb(runtime_db_path(settings))
