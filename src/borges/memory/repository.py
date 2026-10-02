from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from borges.memory.entry import MemoryEntry
from borges.memory.kinds import MAX_PAYLOAD_BYTES, PUBLIC_TENANT, MemoryKind, policy_for
from borges.memory.seal import Sealer, SealError


class MemoryUnavailable(RuntimeError):
    pass


@dataclass
class Loaded:
    entries: list[MemoryEntry] = field(default_factory=list)
    unreadable: int = 0


def _tenant(tenant: str) -> str:
    if not isinstance(tenant, str) or not tenant.strip():
        raise ValueError("every memory query needs a tenant")
    return tenant


def _aad(tenant: str, kind: MemoryKind, dataset_fp: str, signature: str) -> str:
    return f"{tenant}|{kind.value}|{dataset_fp}|{signature}"


class MemoryRepository:
    """Every method takes the tenant first and puts it in every statement."""

    def __init__(
        self, conn: sqlite3.Connection, sealer: Sealer, clock: Callable[[], float] = time.time
    ) -> None:
        self.conn = conn
        self.sealer = sealer
        self.clock = clock

    def storable(self, tenant: str) -> bool:
        return self.sealer.encrypted or _tenant(tenant) == PUBLIC_TENANT

    def put(self, tenant: str, entry: MemoryEntry) -> bool:
        tenant = _tenant(tenant)
        if not self.storable(tenant):
            raise MemoryUnavailable("BORGES_MEMORY_KEY is not set: named tenants are not stored")
        kind, policy, now = entry.kind, policy_for(entry.kind), self.clock()
        aad = _aad(tenant, kind, entry.dataset_fp, entry.signature)
        blob = self.sealer.seal(tenant, aad, entry.payload)
        if len(blob) > MAX_PAYLOAD_BYTES:
            return False
        self.conn.execute(
            f"INSERT INTO {kind.table} (tenant, dataset_fp, family_fp, signature, run_id,"
            " agent_id, agent_version, definition_sha, created_at, last_used_at, expires_at,"
            " size, payload) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
            " ON CONFLICT (tenant, dataset_fp, signature) DO UPDATE SET"
            " family_fp=excluded.family_fp, run_id=excluded.run_id, agent_id=excluded.agent_id,"
            " agent_version=excluded.agent_version, definition_sha=excluded.definition_sha,"
            " created_at=excluded.created_at, last_used_at=excluded.last_used_at,"
            " expires_at=excluded.expires_at, size=excluded.size, payload=excluded.payload",
            (
                tenant,
                entry.dataset_fp,
                entry.family_fp,
                entry.signature,
                entry.run_id,
                entry.agent_id,
                entry.agent_version,
                entry.definition_sha,
                now,
                now,
                now + policy.ttl_s,
                len(blob),
                blob,
            ),
        )
        self.conn.commit()
        self._enforce(tenant, kind)
        return True

    def _enforce(self, tenant: str, kind: MemoryKind) -> None:
        policy, table = policy_for(kind), kind.table
        self.conn.execute(
            f"DELETE FROM {table} WHERE tenant = ? AND expires_at <= ?", (tenant, self.clock())
        )
        rows = self.conn.execute(
            f"SELECT id, size FROM {table} WHERE tenant = ? ORDER BY last_used_at DESC, id DESC",
            (tenant,),
        ).fetchall()
        kept_bytes, doomed = 0, []
        for index, row in enumerate(rows):
            kept_bytes += row["size"]
            if index >= policy.max_rows or kept_bytes > policy.max_bytes:
                doomed.append(row["id"])
        for row_id in doomed:
            self.conn.execute(f"DELETE FROM {table} WHERE tenant = ? AND id = ?", (tenant, row_id))
        self.conn.commit()

    def load(
        self,
        tenant: str,
        kind: MemoryKind,
        dataset_fp: str,
        family_fp: str | None = None,
    ) -> Loaded:
        tenant = _tenant(tenant)
        clause, args = "dataset_fp = ?", [dataset_fp]
        if family_fp is not None:
            clause, args = "(dataset_fp = ? OR family_fp = ?)", [dataset_fp, family_fp]
        rows = self.conn.execute(
            f"SELECT * FROM {kind.table} WHERE tenant = ? AND expires_at > ? AND {clause}"
            " ORDER BY id",
            (tenant, self.clock(), *args),
        ).fetchall()
        loaded = Loaded()
        for row in rows:
            aad = _aad(tenant, kind, row["dataset_fp"], row["signature"])
            try:
                payload = self.sealer.open(
                    tenant, aad, bytes(row["payload"]), allow_plain=tenant == PUBLIC_TENANT
                )
            except SealError:
                loaded.unreadable += 1
                continue
            loaded.entries.append(
                MemoryEntry(
                    kind=kind,
                    dataset_fp=row["dataset_fp"],
                    family_fp=row["family_fp"],
                    signature=row["signature"],
                    payload=payload,
                    run_id=row["run_id"],
                    agent_id=row["agent_id"],
                    agent_version=row["agent_version"],
                    definition_sha=row["definition_sha"],
                    created_at=row["created_at"],
                    last_used_at=row["last_used_at"],
                    hits=row["hits"],
                    row_id=row["id"],
                )
            )
        return loaded

    def touch(self, tenant: str, kind: MemoryKind, row_ids: list[int]) -> None:
        tenant = _tenant(tenant)
        for row_id in row_ids:
            self.conn.execute(
                f"UPDATE {kind.table} SET hits = hits + 1, last_used_at = ?"
                " WHERE tenant = ? AND id = ?",
                (self.clock(), tenant, row_id),
            )
        self.conn.commit()

    def counts(self, tenant: str) -> list[dict[str, object]]:
        tenant = _tenant(tenant)
        by_dataset: dict[str, dict[str, object]] = {}
        for kind in MemoryKind:
            rows = self.conn.execute(
                f"SELECT dataset_fp, COUNT(*) AS n, MAX(last_used_at) AS used FROM {kind.table}"
                " WHERE tenant = ? AND expires_at > ? GROUP BY dataset_fp",
                (tenant, self.clock()),
            ).fetchall()
            for row in rows:
                item = by_dataset.setdefault(
                    row["dataset_fp"], {"dataset": row["dataset_fp"], "last_used": 0.0}
                )
                item[kind.value] = row["n"]
                item["last_used"] = max(float(item["last_used"]), float(row["used"]))
        for item in by_dataset.values():
            for kind in MemoryKind:
                item.setdefault(kind.value, 0)
        return sorted(by_dataset.values(), key=lambda item: -float(item["last_used"]))

    def forget(self, tenant: str, dataset_fp: str | None = None) -> dict[str, int]:
        tenant = _tenant(tenant)
        removed: dict[str, int] = {}
        for kind in MemoryKind:
            if dataset_fp is None:
                cursor = self.conn.execute(f"DELETE FROM {kind.table} WHERE tenant = ?", (tenant,))
            else:
                cursor = self.conn.execute(
                    f"DELETE FROM {kind.table} WHERE tenant = ? AND dataset_fp = ?",
                    (tenant, dataset_fp),
                )
            removed[kind.value] = cursor.rowcount
        self.conn.commit()
        return removed

    def close(self) -> None:
        self.conn.close()
