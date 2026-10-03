from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from borges.identity.chain_links import ChainBroken
from borges.telemetry.audit_log import AuditLog

if TYPE_CHECKING:
    from borges.identity.keystore import KeyRecord

CREATED_KIND = "identity.key.created"
REVOKED_KIND = "identity.key.revoked"
MARKERS = (CREATED_KIND, REVOKED_KIND)
OPERATOR = "operator"


class KeyWitness:
    """Remembers which key events the global audit chain attests, to expose a store rollback."""

    def __init__(self, log: AuditLog) -> None:
        self.log = log
        self._offset = 0
        self._created: dict[str, int] = {}
        self._revoked: dict[str, int] = {}

    def record(self, kind: str, record: KeyRecord, reason: str, seq: int) -> None:
        self.log.append(
            kind,
            principal=OPERATOR,
            decision="allow",
            reason=reason,
            data={
                "key_id": record.key_id,
                "name": record.name,
                "scopes": sorted(record.scopes),
                "seq": seq,
            },
        )

    def _scan(self) -> None:
        path: Path = self.log.path
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return
        if size < self._offset:
            self._offset = 0
        if size == self._offset:
            return
        with path.open("rb") as handle:
            handle.seek(self._offset)
            chunk = handle.read(size - self._offset)
        end = chunk.rfind(b"\n") + 1
        self._offset += end
        for raw in chunk[:end].splitlines():
            if not any(marker.encode() in raw for marker in MARKERS):
                continue
            try:
                entry: dict[str, Any] = json.loads(raw)
            except ValueError:
                continue
            self._note(entry)

    def _note(self, entry: dict[str, Any]) -> None:
        data = entry.get("data")
        key_id = data.get("key_id") if isinstance(data, dict) else None
        seq = data.get("seq", 0) if isinstance(data, dict) else 0
        if not isinstance(key_id, str):
            return
        if entry.get("kind") == CREATED_KIND:
            self._created[key_id] = int(seq)
        elif entry.get("kind") == REVOKED_KIND:
            self._revoked[key_id] = int(seq)

    def check(self, path: Path, keys: dict[str, KeyRecord], count: int) -> None:
        self._scan()
        for key_id, seq in self._created.items():
            if key_id not in keys:
                raise _rolled_back(path, count, f"key {key_id} (record {seq}) was created")
        for key_id, seq in self._revoked.items():
            held = keys.get(key_id)
            if held is None or held.revoked_at is None:
                raise _rolled_back(path, count, f"key {key_id} (record {seq}) was revoked")


def _rolled_back(path: Path, count: int, what: str) -> ChainBroken:
    return ChainBroken(
        path,
        count + 1,
        f"the global audit chain records that {what}, but the store does not show it: "
        "the key store and its anchor were rolled back",
    )
