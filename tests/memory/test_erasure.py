from __future__ import annotations

import json
import sqlite3

from borges.config import Settings
from borges.memory import service
from borges.memory.db import db_path
from borges.memory.entry import MemoryEntry
from borges.memory.factory import open_repository
from borges.memory.kinds import PUBLIC_TENANT, MemoryKind
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path

DATASET = "d" * 64
MARKER = "zebra-ledger-7731-confidential"


def raw_bytes(settings: Settings) -> bytes:
    base = db_path(settings)
    blobs = []
    for suffix in ("", "-wal", "-shm"):
        path = base.with_name(base.name + suffix)
        blobs.append(path.read_bytes() if path.exists() else b"")
    return b"".join(blobs)


def row_count(settings: Settings) -> int:
    conn = sqlite3.connect(db_path(settings))
    try:
        return sum(
            conn.execute(f"SELECT COUNT(*) FROM memory_{kind.value}").fetchone()[0]
            for kind in MemoryKind
        )
    finally:
        conn.close()


def test_a_forgotten_note_leaves_no_row_no_plaintext_and_an_audit_without_payload(
    settings: Settings,
) -> None:
    service.add_note(settings, "caller://acme", "acme", DATASET, "amount", f"note {MARKER}")
    keeper = sqlite3.connect(db_path(settings))
    keeper.execute("SELECT COUNT(*) FROM memory_note").fetchone()
    assert row_count(settings) == 1
    assert MARKER.encode() not in raw_bytes(settings)

    removed = service.forget(settings, "caller://acme", "acme")

    assert removed["note"] == 1 and row_count(settings) == 0
    assert MARKER.encode() not in raw_bytes(settings)
    keeper.close()
    records = [r for r in read_records(global_audit_path(settings)) if r.kind == "memory.forget"]
    assert len(records) == 1 and records[0].data["removed"] == 1
    assert MARKER not in json.dumps(
        [r.model_dump(mode="json") for r in read_records(global_audit_path(settings))]
    )


def test_plain_public_rows_do_not_survive_in_free_pages_or_the_wal(settings: Settings) -> None:
    keyless = settings.model_copy(update={"borges_memory_key": None})
    repo = open_repository(keyless)
    repo.put(
        PUBLIC_TENANT,
        MemoryEntry(MemoryKind.NOTE, DATASET, "f", "sig", {"column": "c", "text": MARKER}),
    )
    keeper = sqlite3.connect(db_path(keyless))
    keeper.execute("SELECT COUNT(*) FROM memory_note").fetchone()
    assert MARKER.encode() in raw_bytes(keyless)
    repo.close()

    service.forget(keyless, "operator", PUBLIC_TENANT, DATASET)

    assert row_count(keyless) == 0
    assert MARKER.encode() not in raw_bytes(keyless)
    keeper.close()


def test_eviction_and_expiry_also_overwrite_the_deleted_bytes(settings: Settings) -> None:
    keyless = settings.model_copy(update={"borges_memory_key": None})
    now = [1000.0]
    repo = open_repository(keyless)
    repo.clock = lambda: now[0]
    repo.put(
        PUBLIC_TENANT,
        MemoryEntry(MemoryKind.CODE, DATASET, "f", "old", {"code": f"# {MARKER}"}),
    )
    now[0] += 31 * 86400
    repo.put(
        PUBLIC_TENANT,
        MemoryEntry(MemoryKind.CODE, DATASET, "f", "new", {"code": "x = 1"}),
    )
    repo.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    repo.close()
    assert MARKER.encode() not in raw_bytes(keyless)
