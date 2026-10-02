from __future__ import annotations

import json
from pathlib import Path

from borges.telemetry.audit_log import AuditLog
from borges.telemetry.audit_record import GENESIS_HASH


def test_records_are_chained(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "a" / "audit.jsonl")
    first = log.append("run.lifecycle", run_id="r1", reason="started")
    second = log.append(
        "policy.run", decision="deny", principal="user:x", reason="busy", data={"n": 1}
    )
    assert first is not None and second is not None
    assert (first.seq, second.seq) == (1, 2)
    assert first.prev_hash == GENESIS_HASH
    assert second.prev_hash == first.hash
    assert second.decision == "deny" and second.principal == "user:x"
    assert second.hash == second.seal().hash


def test_a_new_instance_continues_the_chain(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    first = AuditLog(path).append("a")
    second = AuditLog(path).append("b")
    assert first is not None and second is not None
    assert second.seq == 2 and second.prev_hash == first.hash


def test_unserialisable_data_is_stringified(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    record = log.append("x", data={"path": tmp_path})
    assert record is not None
    assert json.loads((tmp_path / "audit.jsonl").read_text())["data"]["path"] == str(tmp_path)


def test_failures_are_counted_not_raised(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    log = AuditLog(blocker / "audit.jsonl")
    assert log.append("x") is None
    assert log.failures == 1
