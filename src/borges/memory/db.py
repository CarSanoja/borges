from __future__ import annotations

import sqlite3
from pathlib import Path

from borges.config import Settings
from borges.memory.kinds import MemoryKind

DB_RELATIVE = Path("memory") / "memory.db"

TABLE = """
CREATE TABLE IF NOT EXISTS {table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant TEXT NOT NULL,
    dataset_fp TEXT NOT NULL,
    family_fp TEXT NOT NULL,
    signature TEXT NOT NULL,
    run_id TEXT NOT NULL,
    agent_id TEXT,
    agent_version TEXT,
    definition_sha TEXT,
    created_at REAL NOT NULL,
    last_used_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0,
    size INTEGER NOT NULL,
    payload BLOB NOT NULL,
    UNIQUE (tenant, dataset_fp, signature)
);
CREATE INDEX IF NOT EXISTS {table}_family ON {table} (tenant, family_fp);
CREATE INDEX IF NOT EXISTS {table}_lru ON {table} (tenant, last_used_at);
"""


def db_path(settings: Settings) -> Path:
    return Path(settings.borges_home) / DB_RELATIVE


def open_memory_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    for kind in MemoryKind:
        conn.executescript(TABLE.format(table=kind.table))
    return conn
