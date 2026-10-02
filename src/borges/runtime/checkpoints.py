from __future__ import annotations

import json
import time
from typing import Any, Protocol

from borges.runtime.db import RuntimeDb


class CheckpointStore(Protocol):
    def save(self, run_id: str, key: str, seq: int, payload: dict[str, Any]) -> None: ...

    def load(self, run_id: str, key: str) -> dict[str, Any] | None: ...

    def with_prefix(self, run_id: str, prefix: str) -> list[tuple[str, int, dict[str, Any]]]: ...

    def last(self, run_id: str) -> dict[str, Any] | None: ...

    def clear(self, run_id: str) -> None: ...


class NullCheckpointStore:
    def save(self, run_id: str, key: str, seq: int, payload: dict[str, Any]) -> None:
        return None

    def load(self, run_id: str, key: str) -> dict[str, Any] | None:
        return None

    def with_prefix(self, run_id: str, prefix: str) -> list[tuple[str, int, dict[str, Any]]]:
        return []

    def last(self, run_id: str) -> dict[str, Any] | None:
        return None

    def clear(self, run_id: str) -> None:
        return None


class SqliteCheckpointStore:
    """Durable checkpoints: one row per (run, key), replaced as the run advances."""

    def __init__(self, db: RuntimeDb) -> None:
        self.db = db

    def save(self, run_id: str, key: str, seq: int, payload: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (run_id, key, seq, payload, created_at)"
                " VALUES (?,?,?,?,?)",
                (run_id, key, seq, json.dumps(payload, default=str), time.time()),
            )

    def load(self, run_id: str, key: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT payload FROM checkpoints WHERE run_id = ? AND key = ?", (run_id, key)
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def with_prefix(self, run_id: str, prefix: str) -> list[tuple[str, int, dict[str, Any]]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT key, seq, payload FROM checkpoints WHERE run_id = ? AND substr(key, 1, ?)"
                " = ? ORDER BY seq, created_at",
                (run_id, len(prefix), prefix),
            ).fetchall()
        return [(r["key"], r["seq"], json.loads(r["payload"])) for r in rows]

    def last(self, run_id: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT key, seq, created_at FROM checkpoints WHERE run_id = ?"
                " ORDER BY created_at DESC, seq DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM checkpoints WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "key": row["key"],
            "seq": row["seq"],
            "saved_at": row["created_at"],
            "checkpoints": count["n"],
        }

    def clear(self, run_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM checkpoints WHERE run_id = ?", (run_id,))
