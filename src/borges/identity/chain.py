from __future__ import annotations

import fcntl
import hmac
import json
import time
from pathlib import Path
from typing import Any

from borges.identity.chain_anchor import anchor_failure, anchor_stamp, record_anchor
from borges.identity.chain_links import (
    ChainBroken,
    ChainStatus,
    body_of,
    link_hash,
    split_torn,
)
from borges.identity.store_key import derive_key
from borges.telemetry.audit_record import GENESIS_HASH
from borges.telemetry.hashing import canonical_json, sha256_json

MIGRATED = "store.migrated"


class ChainedJsonl:
    """Append-only JSONL chained by prev_hash and hash, keyed and anchored when asked."""

    def __init__(
        self,
        path: Path,
        key: str | None = None,
        domain: str = "chain",
        anchor_path: Path | None = None,
        allow_legacy: bool = False,
    ) -> None:
        self.path = Path(path)
        self.anchor_path = Path(anchor_path) if anchor_path is not None else None
        self.allow_legacy = allow_legacy
        self.keyed = bool(key)
        self._chain_key = derive_key(key, domain, "chain") if key else None
        self._anchor_key = derive_key(key, domain, "anchor") if key else None
        self._cache: tuple[Any, list[dict[str, Any]], ChainStatus] | None = None

    def _stamp(self) -> tuple[Any, Any] | None:
        try:
            info = self.path.stat()
        except FileNotFoundError:
            return None
        return (info.st_mtime_ns, info.st_size), anchor_stamp(self.anchor_path)

    def _wrong_key_hint(self, body: dict[str, Any], prev: str, claimed: str) -> str:
        if self.keyed and link_hash(body, prev) == claimed:
            return "the store was written without a store key but one is configured now"
        return "record hash does not match its content"

    def _load(
        self, text: str, pending_ok: bool = False
    ) -> tuple[list[dict[str, Any]], ChainStatus]:
        events: list[dict[str, Any]] = []
        legacy_rows: list[dict[str, Any]] = []
        prev, hashed = GENESIS_HASH, 0
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
                if not self.allow_legacy:
                    raise ChainBroken(
                        self.path, number, "unhashed record in a store with no legacy"
                    )
                if hashed:
                    raise ChainBroken(self.path, number, "unhashed record after a hashed one")
                legacy_rows.append(record)
                events.append(record)
                continue
            if record.get("prev_hash") != prev:
                raise ChainBroken(self.path, number, "prev_hash does not match the previous record")
            body = body_of(record)
            if not hmac.compare_digest(str(record["hash"]), link_hash(body, prev, self._chain_key)):
                raise ChainBroken(
                    self.path, number, self._wrong_key_hint(body, prev, str(record["hash"]))
                )
            if (
                legacy_rows
                and not hashed
                and record.get("legacy_digest") != sha256_json(legacy_rows)
            ):
                raise ChainBroken(
                    self.path, number, "legacy records are not attested by the first hashed record"
                )
            prev, hashed = record["hash"], hashed + 1
            events.append(record)
        if legacy_rows and not hashed and not pending_ok:
            raise ChainBroken(
                self.path, 1, "legacy records have no attestation; open the store through borges"
            )
        status = ChainStatus(
            ok=True,
            records=len(events),
            head_hash=prev,
            legacy=len(legacy_rows),
            keyed=self.keyed,
            anchored=self.anchor_path is not None,
        )
        return events, status

    def _check_anchor(self, events: list[dict[str, Any]]) -> None:
        if self.anchor_path is None:
            return
        failure = anchor_failure(self.anchor_path, self._anchor_key, events, self.keyed)
        if failure is not None:
            raise ChainBroken(self.path, failure[0], failure[1])

    def read(self) -> list[dict[str, Any]]:
        stamp = self._stamp()
        if stamp is None:
            self._check_anchor([])
            return []
        if self._cache is not None and self._cache[0] == stamp:
            return self._cache[1]
        events, status = self._load(split_torn(self.path.read_text(encoding="utf-8"))[0])
        self._check_anchor(events)
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
                keyed=self.keyed,
                anchored=self.anchor_path is not None,
            )
        if self._cache is None:
            return ChainStatus(
                ok=True,
                records=0,
                head_hash=GENESIS_HASH,
                keyed=self.keyed,
                anchored=self.anchor_path is not None,
            )
        return self._cache[2]

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            raw = handle.read()
            complete, torn = split_torn(raw)
            events, status = self._load(complete, pending_ok=True)
            self._check_anchor(events)
            if torn:
                with self.path.with_name(self.path.name + ".torn").open("a", encoding="utf-8") as q:
                    q.write(torn + "\n")
                handle.truncate(len(complete.encode("utf-8")))
            elif raw and not raw.endswith("\n"):
                handle.write("\n")
            body = {"seq": len(events) + 1, "ts": time.time(), **event}
            if status.legacy and len(events) == status.legacy:
                body["legacy_digest"] = sha256_json(events)
            record = {
                **body,
                "prev_hash": status.head_hash,
                "hash": link_hash(body, status.head_hash, self._chain_key),
            }
            handle.write(canonical_json(record) + "\n")
            handle.flush()
            if self.anchor_path is not None:
                record_anchor(self.anchor_path, self._anchor_key, body["seq"], record["hash"])
        self._cache = None
        return record

    def attest_legacy(self) -> bool:
        if not self.path.is_file():
            return False
        _, status = self._load(split_torn(self.path.read_text(encoding="utf-8"))[0], True)
        if not status.legacy or status.records != status.legacy:
            return False
        self.append({"event": MIGRATED, "legacy_records": status.legacy})
        return True
