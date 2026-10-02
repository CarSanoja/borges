from __future__ import annotations

from borges.config import Settings
from borges.runtime import audit

READ = "memory.read"
WRITE = "memory.write"
FORGET = "memory.forget"
SHORT = 12


def record_read(
    settings: Settings,
    principal: str | None,
    tenant: str,
    kind: str,
    dataset: str,
    rows: int,
    usable: int,
) -> None:
    audit.record(
        settings,
        READ,
        principal=principal,
        data={
            "tenant": tenant,
            "memory_kind": kind,
            "dataset": dataset[:SHORT],
            "rows": rows,
            "usable": usable,
        },
    )


def record_write(
    settings: Settings, principal: str | None, tenant: str, kind: str, dataset: str, rows: int
) -> None:
    audit.record(
        settings,
        WRITE,
        principal=principal,
        data={"tenant": tenant, "memory_kind": kind, "dataset": dataset[:SHORT], "rows": rows},
    )


def record_forget(
    settings: Settings,
    principal: str | None,
    tenant: str,
    dataset: str | None,
    removed: dict[str, int],
) -> None:
    audit.record(
        settings,
        FORGET,
        principal=principal,
        data={
            "tenant": tenant,
            "dataset": dataset[:SHORT] if dataset else "all",
            "removed": sum(removed.values()),
            "by_kind": removed,
        },
    )
