from __future__ import annotations

from borges.config import Settings
from borges.memory import audit
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import global_audit_path


def records(settings: Settings, kind: str):
    return [r for r in read_records(global_audit_path(settings)) if r.kind == kind]


def test_reads_and_writes_carry_tenant_and_principal_but_no_payload(settings: Settings) -> None:
    audit.record_read(settings, "caller://ops", "ops", "verdict", "f" * 64, rows=3, usable=2)
    audit.record_write(settings, "caller://ops", "ops", "code", "f" * 64, rows=4)
    (read,) = records(settings, "memory.read")
    (write,) = records(settings, "memory.write")
    assert read.principal == "caller://ops"
    assert read.data == {
        "tenant": "ops",
        "memory_kind": "verdict",
        "dataset": "f" * 12,
        "rows": 3,
        "usable": 2,
    }
    assert write.data["rows"] == 4 and write.data["tenant"] == "ops"


def test_forget_is_recorded_with_the_scope_and_counts(settings: Settings) -> None:
    audit.record_forget(settings, "operator", "ops", None, {"verdict": 2, "code": 1})
    audit.record_forget(settings, "operator", "ops", "a" * 64, {"verdict": 1})
    first, second = records(settings, "memory.forget")
    assert first.data["dataset"] == "all" and first.data["removed"] == 3
    assert second.data["dataset"] == "a" * 12
