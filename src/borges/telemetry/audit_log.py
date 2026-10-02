from __future__ import annotations

import fcntl
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from borges.telemetry.audit_record import GENESIS_HASH, AuditRecord, Decision

_LOCK = threading.RLock()
TAIL_BYTES = 65536


def _last_line(handle: Any) -> bytes:
    handle.seek(0, os.SEEK_END)
    position = handle.tell()
    chunks: list[bytes] = []
    while position > 0:
        step = min(TAIL_BYTES, position)
        position -= step
        handle.seek(position)
        chunks.insert(0, handle.read(step))
        lines = [line for line in b"".join(chunks).splitlines() if line.strip()]
        if len(lines) > 1 or (lines and position == 0):
            return lines[-1]
    return b""


def read_tail(path: Path) -> tuple[int, str]:
    try:
        with path.open("rb") as handle:
            line = _last_line(handle)
    except FileNotFoundError:
        return 0, GENESIS_HASH
    if not line:
        return 0, GENESIS_HASH
    last = json.loads(line)
    return int(last["seq"]), str(last["hash"])


class AuditLog:
    """Append-only, hash-chained JSONL: each record carries prev_hash and its own sha256."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.failures = 0

    def append(
        self,
        kind: str,
        *,
        run_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        principal: str | None = None,
        decision: Decision | None = None,
        reason: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> AuditRecord | None:
        try:
            return self._append(
                kind, run_id, trace_id, span_id, principal, decision, reason, data or {}
            )
        except Exception:
            self.failures += 1
            return None

    def _append(
        self,
        kind: str,
        run_id: str | None,
        trace_id: str | None,
        span_id: str | None,
        principal: str | None,
        decision: Decision | None,
        reason: str | None,
        data: dict[str, Any],
    ) -> AuditRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK, self.path.open("a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                seq, prev_hash = read_tail(self.path)
                record = AuditRecord(
                    seq=seq + 1,
                    ts=datetime.now(UTC).isoformat(timespec="microseconds"),
                    kind=kind,
                    run_id=run_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    principal=principal,
                    decision=decision,
                    reason=reason,
                    data=json.loads(json.dumps(data, default=str)),
                    prev_hash=prev_hash,
                ).seal()
                handle.write((record.line() + "\n").encode("utf-8"))
                handle.flush()
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
        return record
