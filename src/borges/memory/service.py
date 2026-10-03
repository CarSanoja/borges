from __future__ import annotations

from typing import Any

from borges.armor.report import ArmorReport
from borges.config import Settings
from borges.memory import audit
from borges.memory.entry import MemoryEntry
from borges.memory.factory import open_repository
from borges.memory.kinds import POLICIES, MemoryKind
from borges.memory.repository import MemoryUnavailable
from borges.memory.screening import screen_payload
from borges.memory.signatures import note_signature
from borges.memory.tenant import MemoryMode, resolve_mode, tenant_of

MAX_NOTE_CHARS = 500
MAX_COLUMN_CHARS = 120


def describe(settings: Settings, principal_id: str | None) -> dict[str, Any]:
    mode = resolve_mode(settings, principal_id)
    tenant = tenant_of(principal_id)
    repo = open_repository(settings)
    try:
        datasets = repo.counts(tenant)
    finally:
        repo.close()
    totals = {kind.value: sum(int(d[kind.value]) for d in datasets) for kind in MemoryKind}
    return {
        "tenant": tenant,
        "mode": mode.label,
        "enabled": mode.enabled,
        "encrypted": mode.encrypted,
        "note": mode.reason or _mode_note(mode),
        "totals": totals,
        "datasets": datasets,
        "limits": {
            kind.value: {"ttl_days": p.ttl_s / 86400, "max_rows": p.max_rows}
            for kind, p in POLICIES.items()
        },
    }


def _mode_note(mode: MemoryMode) -> str:
    if mode.label == "public-demo":
        stored = "encrypted" if mode.encrypted else "stored unencrypted"
        return f"Shared by all visitors, curated cases only, {stored}."
    return "Encrypted at rest and visible only to this key."


def forget(
    settings: Settings, actor: str | None, tenant: str, dataset: str | None = None
) -> dict[str, int]:
    repo = open_repository(settings)
    try:
        removed = repo.forget(tenant, dataset)
    finally:
        repo.close()
    audit.record_forget(settings, actor, tenant, dataset, removed)
    return removed


def add_note(
    settings: Settings,
    actor: str | None,
    tenant: str,
    dataset: str,
    column: str,
    text: str,
) -> None:
    column, text = column.strip(), text.strip()
    if not column or len(column) > MAX_COLUMN_CHARS:
        raise ValueError(f"a note names one column of at most {MAX_COLUMN_CHARS} characters")
    if not text or len(text) > MAX_NOTE_CHARS:
        raise ValueError(f"a note has 1 to {MAX_NOTE_CHARS} characters")
    report = ArmorReport()
    payload = screen_payload(MemoryKind.NOTE, {"column": column, "text": text}, report, "note")
    if report:
        audit.record_screened(
            settings, actor, tenant, MemoryKind.NOTE.value, "write", report.decisions
        )
    if payload is None or payload["text"] != text:
        raise ValueError("the note looks like an instruction to a model or holds personal data")
    repo = open_repository(settings)
    try:
        if not repo.storable(tenant):
            raise MemoryUnavailable("BORGES_MEMORY_KEY is not set: named tenants are not stored")
        repo.put(
            tenant,
            MemoryEntry(
                kind=MemoryKind.NOTE,
                dataset_fp=dataset,
                family_fp="",
                signature=note_signature(column),
                payload=payload,
                run_id="owner",
            ),
        )
    finally:
        repo.close()
    audit.record_write(settings, actor, tenant, MemoryKind.NOTE.value, dataset, 1)
