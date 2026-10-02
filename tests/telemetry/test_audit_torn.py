from __future__ import annotations

from pathlib import Path

from borges.telemetry.audit_log import AuditLog
from borges.telemetry.audit_torn import torn_path
from borges.telemetry.audit_verify import read_records, verify_chain


def test_torn_last_line_is_quarantined_and_the_chain_continues(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append("a")
    log.append("b")
    with path.open("ab") as handle:
        handle.write(b'{"v":1,"seq":3,"ts":"2026')
    appended = log.append("c")
    assert appended is not None
    kinds = [r.kind for r in read_records(path)]
    assert kinds == ["a", "b", "audit.torn_line", "c"]
    assert verify_chain(path).ok
    assert torn_path(path).read_bytes().startswith(b'{"v":1,"seq":3')
    notice = read_records(path)[2]
    assert notice.decision == "observe" and notice.data["bytes"] > 0
    assert notice.data["quarantine"] == "audit.jsonl.torn"
    assert log.failures == 0


def test_intact_file_creates_no_quarantine(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append("a")
    log.append("b")
    assert not torn_path(path).exists()
    assert [r.kind for r in read_records(path)] == ["a", "b"]


def test_complete_record_missing_only_its_newline_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append("a")
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    log.append("b")
    assert [r.kind for r in read_records(path)] == ["a", "b"]
    assert verify_chain(path).ok and not torn_path(path).exists()


def test_file_that_is_only_a_torn_fragment(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_bytes(b'{"seq": 1, "kin')
    log = AuditLog(path)
    log.append("a")
    assert [r.kind for r in read_records(path)] == ["audit.torn_line", "a"]
    assert verify_chain(path).ok
