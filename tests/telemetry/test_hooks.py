from __future__ import annotations

from pathlib import Path

from borges.config import Settings
from borges.telemetry import hooks
from borges.telemetry.audit_verify import read_records
from borges.telemetry.run_telemetry import RunTelemetry


def test_hooks_are_noops_without_telemetry() -> None:
    assert hooks.current() is None
    hooks.audit("x", reason="r")
    with hooks.span("stage", "s") as span:
        span.set_attribute("a", 1)


def test_audit_inside_a_span_links_span_and_trace(tmp_path: Path) -> None:
    telemetry = RunTelemetry.open(
        Settings(_env_file=None, borges_home=tmp_path / "home"), "r1", tmp_path / "run"
    )
    with (
        hooks.bound(telemetry),
        telemetry.span("run", "run r1"),
        hooks.span("stage", "stage planning"),
    ):
        hooks.audit("policy.x", decision="deny", reason="no", principal="user:a", n=1)
    telemetry.close()
    record = read_records(tmp_path / "run" / "audit.jsonl")[0]
    assert record.decision == "deny" and record.principal == "user:a" and record.data == {"n": 1}
    assert record.trace_id == telemetry.trace_id and len(record.span_id or "") == 16
    assert hooks.current() is None
