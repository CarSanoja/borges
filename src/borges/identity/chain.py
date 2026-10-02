from __future__ import annotations

import fcntl
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from borges.telemetry.audit_record import GENESIS_HASH
from borges.telemetry.hashing import canonical_json, sha256_text

HASH_FIELDS = ("prev_hash", "hash")


class ChainBroken(RuntimeError):
    def __init__(self, path: Path, line: int, reason: str) -> None:
        self.path = Path(path)
        self.line = line
        self.reason = reason
        super().__init__(
            f"{self.path} failed hash-chain verification at line {line}: {reason}. "
            "The file was edited or truncated; refusing to use it."
        )


@dataclass(frozen=True)
class ChainStatus:
    ok: bool
    records: int
    head_hash: str
    legacy: int = 0
    broken_line: int | None = None
    reason: str | None = None


def link_hash(body: dict[str, Any], prev_hash: str) -> str:
    return sha256_text(canonical_json({**body, "prev_hash": prev_hash}))


def _body(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in HASH_FIELDS}


class ChainedJsonl:
    """Append-only JSONL chained by prev_hash and hash; a leading unhashed prefix is legacy."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._cache: tuple[tuple[int, int], list[dict[str, Any]], ChainStatus] | None = None

    def _stamp(self) -> tuple[int, int] | None:
        try:
            info = self.path.stat()
        except FileNotFoundError:
            return None
        return info.st_mtime_ns, info.st_size

    def _load(self, text: str) -> tuple[list[dict[str, Any]], ChainStatus]:
        events: list[dict[str, Any]] = []
        prev, legacy = GENESIS_HASH, 0
        for number, raw in enumerate(text.splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except ValueError as exc:
                raise ChainBroken(self.path, number, f"unreadable record: {exc}") from exc
            if not isinstance(record, dict):
                raise ChainBroken(self.path, number, "record is not an object")
            if "hash" not in record:
                if len(events) != legacy:
                    raise ChainBroken(self.path, number, "unhashed record after a hashed one")
                head = link_hash(record, prev)
                events.append({**record, "prev_hash": prev, "hash": head})
                prev, legacy = head, legacy + 1
                continue
            if record.get("prev_hash") != prev:
                raise ChainBroken(self.path, number, "prev_hash does not match the previous record")
            if link_hash(_body(record), prev) != record["hash"]:
                raise ChainBroken(self.path, number, "record hash does not match its content")
            prev = record["hash"]
            events.append(record)
        return events, ChainStatus(ok=True, records=len(events), head_hash=prev, legacy=legacy)

    def read(self) -> list[dict[str, Any]]:
        stamp = self._stamp()
        if stamp is None:
            return []
        if self._cache is not None and self._cache[0] == stamp:
            return self._cache[1]
        events, status = self._load(self.path.read_text(encoding="utf-8"))
        self._cache = (stamp, events, status)
        return events

    def verify(self) -> ChainStatus:
        try:
            self.read()
        except ChainBroken as broken:
            return ChainStatus(
                ok=False,
                records=0,
                head_hash=GENESIS_HASH,
                broken_line=broken.line,
                reason=broken.reason,
            )
        if self._cache is None:
            return ChainStatus(ok=True, records=0, head_hash=GENESIS_HASH)
        return self._cache[2]

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            events, status = self._load(handle.read())
            body = {"seq": len(events) + 1, "ts": time.time(), **event}
            record = {
                **body,
                "prev_hash": status.head_hash,
                "hash": link_hash(body, status.head_hash),
            }
            handle.write(canonical_json(record) + "\n")
            handle.flush()
        self._cache = None
        return record

    def seal_legacy(self) -> int:
        events = self.read()
        if not events:
            return 0
        lines = [canonical_json(e) for e in events]
        fd, name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write("\n".join(lines) + "\n")
        os.replace(name, self.path)
        self._cache = None
        return len(events)
